#!/usr/bin/env python

import os
import configparser
import argparse
import re
import requests
import logging
import git
from datetime import datetime
from github import Github
from tabulate import tabulate

from . import logger
from . import auth
from . import cfg

log = logger.logger

def list_command(github, github_repo, only_mine=False):
    pulls = github_repo.get_pulls(state='open', sort='created')
    if only_mine:
        user_id = github.get_user().id
        pulls = [pull for pull in pulls if pull.user.id == user_id]
    pulls_table = [[pull.number, pull.title[:60], pull.head.ref] for pull in pulls]
    if any(pulls_table):
        print('\n' + tabulate(pulls_table, ['#', 'Title', 'Branch']))
    else:
        print('No pull requests found')


def merge_command(git_repo, github_repo, pull_number):
    log.info(f'Merging Pull Request #{pull_number}')

    # This undo stack is used when we want to back out of changes
    undo_stack = []
    class UndoAction(object):
        def __init__(self, action, failure_is_fatal=False):
            self.action = action
            self.failure_is_fatal = failure_is_fatal

    # Find the pull request
    pull = None
    try:
        pull = github_repo.get_pull(pull_number)
    except Exception as ex:
        log.error(f'Could not find pull request with number {pull_number}\n    {ex})')
        exit(1)

    # Has it already been merged?
    if pull.merged:
        log.error("This pull request has already been merged.")
        exit(1)

    # Is the pr closed?
    if pull.state == 'closed':
        log.error("This pull request is closed")
        exit(1)

    # Is this pr mergeable?
    if not pull.mergeable or not pull.rebaseable:
        log.error("""This pull request is not mergeable. This could be due to any of the following:
  - The pull request merge is blocked by validation rules in this repo
  - The pull request has merge conflicts""")

        # Ask to if user wants to proceed anyway
        confirm_continue_answer = input(f"Do you want to proceed anyway? (y/n) ") or "n"
        if confirm_continue_answer.lower() != 'y':
            exit(1)

    # Utility methods
    def is_branch_in_rebaseable_state(branch):
        # Are we tracking the branch locally?
        if branch not in git_repo.refs:
            return True

        # Branch is being tracked locally, check if we've diverged
        base_commits_diff = git_repo.git.rev_list('--left-right', '--count', f'{branch}...{branch}@{{u}}')
        num_commits_ahead, _ = base_commits_diff.split('\t')
        has_diverged = int(num_commits_ahead) > 0
        return not has_diverged

    def revert_back_to_original_state():
        while len(undo_stack) > 0:
            action = undo_stack.pop()
            try:
                action.action()
            except Exception as ex:
                if action.failure_is_fatal:
                    log.fatal(f'An unexpected error occurred: {ex}')
                    break
                else:
                    log.error(f'An unexpected error occurred: {ex}')

    # Has the base branch diverged from remote?
    if not is_branch_in_rebaseable_state(pull.base.ref):
        log.error(f'The local base branch `{pull.base.ref}` has diverged from remote. Update the branch before continuing')
        exit(1)

    # Has the pr branch diverged from remote?
    if not is_branch_in_rebaseable_state(pull.head.ref):
        log.error(f'The local branch `{pull.head.ref}` has diverged from remote. Update the branch before continuing')
        exit(1)

    ## Do Linear Merge
    #  1. Stash local changes if necessary
    #  2. Fetch from origin
    #  3. Checkout the pull request branch & update it
    #  4. Create a backup branch before rebasing
    #  5. Rebase the pull request branch & force-push to origin
    #  6. Checkout pull request base branch
    #  7. Merge pull request branch into base
    #  8. Ask user for confirmation
    #  9. Push base branch
    # 10. Delete pull request branch
    # 11. Delete backup branch
    # 12. Checkout the branch the user was originally on
    # 13. Re-apply local stash if necessary
    try:
        # Stash local changes if needed
        if git_repo.is_dirty(untracked_files=True):
            log.info('Stashing local changes')
            git_repo.git.stash('push')

            def reapply_stash():
                log.info(f'Re-applying stashed changes')
                git_repo.git.stash('pop')
            undo_stack.append(UndoAction(reapply_stash))

        # Preserve the current branch the user was on, so that we can go back after completion
        orig_branch = git_repo.active_branch
        def go_back_to_original_branch():
            log.info(f'Checking out original branch {orig_branch}')
            git_repo.git.checkout(orig_branch)
        undo_stack.append(UndoAction(go_back_to_original_branch))

        # Fetch so we're operating on the latest data
        log.info('Fetching')
        git_repo.remotes.origin.fetch()

        # Checkout the pr branch and bring it up to date if necessary
        log.info(f'Checking out {pull.head.ref}')
        git_repo.git.checkout(pull.head.ref)
        log.info(f'Updating {pull.head.ref}')
        git_repo.git.pull('--rebase')

        # Create a backup branch before rebasing
        backup_branch_timestamp = datetime.now().strftime('%H-%M-%S')
        backup_branch_name = f'backup/{pull.head.ref}-{backup_branch_timestamp}'
        log.info(f'Creating a backup branch before rebasing: {backup_branch_name}')
        git_repo.create_head(backup_branch_name)
        def delete_backup_branch():
            log.info(f'Deleting the local backup branch {backup_branch_name}')
            git_repo.git.branch('-d', backup_branch_name)
        undo_stack.append(UndoAction(delete_backup_branch))

        # Rebase the pr branch on top of the base (remote)
        def undo_rebase():
            log.info(f'Undoing rebase')
            log.info(f'Reverting {pull.head.ref} back to original state at {backup_branch_name}')
            try:
                git_repo.git.rebase('--abort')
            except Exception:
                pass
            git_repo.git.reset('--hard')
            git_repo.git.checkout(pull.head.ref)
            git_repo.git.reset('--hard', backup_branch_name)
            log.info(f'Force-pushing {pull.head.ref}')
            git_repo.git.push('-f', '--no-verify')
        undo_rebase_action = UndoAction(undo_rebase, failure_is_fatal=True)
        undo_stack.append(undo_rebase_action)

        log.info(f'Updating {pull.base.ref}')
        git_repo.git.fetch('origin', f'{pull.base.ref}:{pull.base.ref}')
        log.info(f'Rebasing {pull.head.ref} onto {pull.base.ref}')
        git_repo.git.rebase(pull.base.ref)
        log.info(f'Force-pushing {pull.head.ref}')
        git_repo.git.push('origin', '-f', '--no-verify', pull.head.ref)

        # Checkout the base branch and bring it up to date if necessary
        log.info(f'Checking out {pull.base.ref}')
        git_repo.git.checkout(pull.base.ref)
        log.info(f'Updating {pull.base.ref}')
        git_repo.git.pull('--rebase')

        # Merge pr branch into base
        def undo_pr_merge():
            log.info(f'Undoing merge')
            try:
                git_repo.git.merge('--abort')
            except Exception:
                pass
            git_repo.git.checkout(pull.base.ref)
            git_repo.git.reset('--hard', f'{pull.base.ref}@{{u}}')
        undo_pr_merge_action = UndoAction(undo_pr_merge, failure_is_fatal=True)
        undo_stack.append(undo_pr_merge_action)

        log.info(f'Merging {pull.head.ref} into {pull.base.ref}')
        merge_msg = f'Merge: {pull.title} (#{pull.number})\n\n{pull.body}'
        git_repo.git.merge(pull.head.ref, '--no-ff', '-m', merge_msg)

        # Ask for permission to push
        num_commits_to_push = len(list(git_repo.iter_commits(f'{pull.base.ref}...{pull.base.ref}@{{u}}')))
        preview_history = git_repo.git.log('--pretty=format:"%h %s"', '--graph', f'-{num_commits_to_push+1}')
        print(preview_history)
        confirm_merge_answer = input(f"Does this look correct? (y/n) ") or "n"

        # Push the merge
        if confirm_merge_answer.lower() == 'y':
            # Check that the base branch has not been updated since
            git_repo.remotes.origin.fetch()
            base_commits_diff = git_repo.git.rev_list('--left-right', '--count', f'{pull.base.ref}...{pull.base.ref}@{{u}}')
            _, num_behind = base_commits_diff.split('\t')

            # Can we continue?
            if int(num_behind) > 0:
                log.error(f'The base branch `{pull.base.ref}` has been updated since we started. Try running this script again')
            else:
                # Push
                log.info(f'Pushing {pull.base.ref}')
                git_repo.git.push('origin', '--no-verify', pull.base.ref)
                log.info(f'Successfully merged Pull Request #{pull.number}')

                # Pop some elements
                undo_stack.remove(undo_rebase_action)
                undo_stack.remove(undo_pr_merge_action)

                # Delete the pr branch
                log.info(f'Deleting the pull request branch {pull.head.ref}')
                git_repo.git.push('origin', '--delete', '--no-verify', pull.head.ref)

    except git.CommandError as command_error:
        command = command_error._cmdline
        output = command_error.stdout[12:-1] if len(command_error.stdout) > 0 else ''
        output = output.replace('\n', '\n> ')
        log.error(f'An unexpected git error occurred:\n> {command}\n> {output}')

    except Exception as ex:
        log.error(f'An unexpected error occurred: {ex}')

    finally:
        # Done! Apply all necessary actions to go back to the starting state
        revert_back_to_original_state()


def run():
    # Command line arg parsing
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Merges github pull requests by rebasing before merging to maintan linear history"
    )
    parser.add_argument('-t', '--token', help='Github access token to use')
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
    subparsers = parser.add_subparsers(title='Commands', dest='cmd')
    subparsers.required = True
    list_command_parser = subparsers.add_parser('list', aliases=['ls'])
    list_command_parser.add_argument('-m', '--mine', action='store_true', help='List only pull requests opened by me')
    merge_command_parser = subparsers.add_parser('merge')
    merge_command_parser.add_argument('number', type=int, nargs=1, help='pull request number')
    args = vars(parser.parse_args())

    # Logging setup
    logger.setup_logging(logging.DEBUG if args['verbose'] else logging.INFO)

    # Load config
    config_file_path = os.path.expanduser(f'~/{cfg.RC_FILE_NAME}')
    config = configparser.ConfigParser()
    config.read(config_file_path)
    github_access_token = args['token']
    if not github_access_token:
        github_access_token = config.get('auth', 'github_access_token')

    # Auth checkup
    github_access_token = auth.initial_auth_flow_if_necessary(github_access_token)

    # Repo setup
    git_repo = None
    try:
        git_repo = git.Repo(search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        log.error('This directory is not a valid git repository')
        exit(1)
    git_remote_urls = [url for urls in [list(r.urls) for r in git_repo.remotes] for url in urls]
    github_remote_urls = [url for url in git_remote_urls if 'github.com' in url]
    if not any(github_remote_urls):
        log.error('This is not a Github repository')
        exit(1)

    # Parse github repo name from remote url:
    # https://github.com/spatialsys/Spatial-2.0.git
    # git@github.com:spatialsys/Spatial-2.0.git
    github_repo_name = re.search(r'.*[:/](.*/.*)\.git', github_remote_urls[0]).group(1)

    # Github setup
    github = Github(github_access_token)
    github_repo = github.get_repo(github_repo_name)

    # Run the command
    if args['cmd'] == 'list':
        list_command(github, github_repo, args['mine'])
    elif args['cmd'] == 'merge':
        merge_command(git_repo, github_repo, args['number'][0])


if __name__ == '__main__':
    run()
