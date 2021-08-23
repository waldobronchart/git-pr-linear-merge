#!/usr/bin/env python

import os
import configparser
import argparse
import re
import requests
import logging
import git
import colorama
from datetime import datetime
from github import Github
from tabulate import tabulate
from itertools import groupby

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


def merge_command(merge_with_squash, git_repo, github_repo, pull_number, merge_config):
    log.info(f'{colorama.Fore.CYAN}Preparing to merge Pull Request #{pull_number}')

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

    # Fetch so we're operating on the latest data
    log.info('Fetching')
    git_repo.remotes.origin.fetch()

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
    # 10. Delete pull request branch (local and remote)
    # 11. Delete backup branch
    # 12. Checkout the branch the user was originally on (if user wasn't on the pr branch)
    # 13. Re-apply local stash if necessary
    try:
        # Stash local changes if needed
        if git_repo.is_dirty(untracked_files=True):
            log.info('Stashing local changes')
            git_repo.git.stash('push', '--include-untracked')

            def reapply_stash():
                log.info(f'Re-applying stashed changes')
                git_repo.git.stash('pop')
            undo_stack.append(UndoAction(reapply_stash))

        # Preserve the current branch the user was on, so that we can go back after completion
        orig_branch = git_repo.active_branch
        def go_back_to_original_branch():
            log.info(f'Checking out original branch {orig_branch}')
            git_repo.git.checkout(orig_branch)
        checkout_original_branch = UndoAction(go_back_to_original_branch)
        undo_stack.append(checkout_original_branch)

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
            git_repo.git.branch('-D', backup_branch_name)
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
        log.info(f'{colorama.Fore.CYAN}Rebasing {pull.head.ref} onto {pull.base.ref}')
        git_repo.git.rebase(pull.base.ref)
        log.info(f'Force-pushing {pull.head.ref}')
        git_repo.git.push('origin', '-f', '--no-verify', pull.head.ref)

        # Checkout the base branch and bring it up to date if necessary
        log.info(f'Checking out {pull.base.ref}')
        git_repo.git.checkout(pull.base.ref)
        git_repo.git.branch(f'--set-upstream-to=origin/{pull.base.ref}', pull.base.ref) # Fixes an issue where checkout didn't track the upstream
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

        num_commits_on_branch = len(list(git_repo.iter_commits(f'{pull.base.ref}...{pull.head.ref}@{{u}}')))
        if num_commits_on_branch == 1 and merge_config.always_squash_single_commit_pulls:
            merge_with_squash = True

        commit_msg_format = merge_config.squash_msg_format if merge_with_squash else merge_config.merge_msg_format
        merge_msg = commit_msg_format.format(
            TITLE=pull.title,
            NUMBER=pull.number,
            AUTHOR_USERNAME=pull.user.login,
            AUTHOR_NAME=pull.user.name
        )
        if merge_with_squash:
            # Find author to attribute the commit to (select author with most commits on branch)
            commit_log = git_repo.git.log(pull.head.sha, '-n', num_commits_on_branch)
            commit_authors = sorted(list(re.findall(r'Author: (.*?)\n', commit_log)))
            commit_authors_count = {k:len(list(g)) for k, g in groupby(commit_authors)}
            main_author = max(commit_authors_count, key=commit_authors_count.get)

            # Do the squash
            log.info(f'{colorama.Fore.CYAN}Squashing {pull.head.ref} onto {pull.base.ref}')
            git_repo.git.merge('--squash', pull.head.sha)
            git_repo.git.commit('--author', main_author, '-m', merge_msg)
        else:
            # Regular merge preserving all commits from the original branch
            log.info(f'{colorama.Fore.CYAN}Merging {pull.head.ref} onto {pull.base.ref}')
            git_repo.git.merge(pull.head.ref, '--no-ff', '-m', merge_msg)

        # Output preview of local base branch with new commits highlighted
        num_commits_to_push = len(list(git_repo.iter_commits(f'{pull.base.ref}...{pull.base.ref}@{{u}}')))
        branch_format_decorated = f'{colorama.Fore.CYAN}{colorama.Back.BLACK}%d{colorama.Style.RESET_ALL}'
        preview_history = git_repo.git.log(f'--pretty=format:%s{branch_format_decorated}', '--graph', f'-{num_commits_to_push+3}').split('\n')
        num_lines_to_highlight = num_commits_to_push + (0 if merge_with_squash else 2)
        new_commit_color_style = f'{colorama.Fore.WHITE}{colorama.Back.YELLOW}'
        for i in range(num_lines_to_highlight):
            preview_history[i] = re.sub(r'^\*(.*?)', f'{new_commit_color_style}*{colorama.Style.RESET_ALL}' + r'\1', preview_history[i], 1)
            preview_history[i] = re.sub(r'^\|(.*?)', f'{new_commit_color_style}|{colorama.Style.RESET_ALL}' + r'\1', preview_history[i], 1)
        log.info(f'Confirm merge:\n  ' + '\n  '.join(preview_history))

        # Ask for permission to push
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
                log.info(f'{colorama.Fore.CYAN}Pushing {pull.base.ref}')
                git_repo.git.push('origin', '--no-verify', pull.base.ref)
                log.info(f'{colorama.Fore.GREEN}Successfully merged Pull Request #{pull.number}')

                # Pop some elements
                undo_stack.remove(undo_rebase_action)
                undo_stack.remove(undo_pr_merge_action)

                # Delete the remote pr branch
                log.info(f'Deleting the pull request branch {pull.head.ref}')
                try: # trycatch here because GitPython seems to throw an error here, even if it succeeds
                    git_repo.git.push('origin', '--delete', '--no-verify', pull.head.ref)
                except:
                    pass

                # Merge was successful, if the original branch was the same as the pr branch, stay on the base branch
                if orig_branch.name == pull.head.ref:
                    # No longer need to go back to original branch
                    undo_stack.remove(checkout_original_branch)

                # Delete local pr branch
                git_repo.git.branch('-D', pull.head.ref)

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
        description="Merges github pull requests by rebasing before merging to maintain linear history"
    )
    parser.add_argument('-t', '--token', help='Github access token to use')
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
    subparsers = parser.add_subparsers(title='Commands', dest='cmd')
    subparsers.required = True
    list_command_parser = subparsers.add_parser('list', aliases=['ls'])
    list_command_parser.add_argument('-m', '--mine', action='store_true', help='List only pull requests opened by me')
    merge_command_parser = subparsers.add_parser('merge')
    merge_command_parser.add_argument('number', type=int, nargs=1, help='pull request number')
    squash_command_parser = subparsers.add_parser('squash')
    squash_command_parser.add_argument('number', type=int, nargs=1, help='pull request number')
    args = vars(parser.parse_args())

    # Logging setup
    colorama.init(autoreset=True)
    logger.setup_logging(logging.DEBUG if args['verbose'] else logging.INFO)

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

    # Load configs
    git_repo_dir = git_repo.git.rev_parse('--show-toplevel')
    global_config_file_path = os.path.expanduser(f'~/{cfg.RC_FILE_NAME}')
    local_config_file_path = os.path.join(git_repo_dir, cfg.RC_FILE_NAME)
    config_files = [global_config_file_path]
    if os.path.exists(local_config_file_path):
        log.debug(f'Reading from local repo config: {local_config_file_path}')
        config_files.insert(0, local_config_file_path)
    config = configparser.ConfigParser()
    config.read(config_files)

    # Auth checkup
    github_access_token = args['token']
    if not github_access_token:
        github_access_token = config.get('auth', 'github_access_token', fallback=None)
    github_access_token = auth.initial_auth_flow_if_necessary(github_access_token)

    # Parse github repo name from remote url:
    # https://github.com/spatialsys/Spatial-2.0.git
    # git@github.com:spatialsys/Spatial-2.0.git
    github_repo_name = re.search(r'.*[:/](.*/.*)\.git', github_remote_urls[0]).group(1)

    # Github setup
    github = Github(github_access_token)
    github_repo = github.get_repo(github_repo_name)

    # Run the command
    if args['cmd'] in ['list', 'ls']:
        list_command(github, github_repo, args['mine'])
    elif args['cmd'] in ['merge', 'squash']:
        merge_config = cfg.MergeConfig(config)

        merge_with_squash = (args['cmd'] == 'squash')
        if merge_with_squash and not merge_config.squash_cmd_enabled:
            log.error('Squash merge is not enabled in local configuration (squash_cmd_enabled = False)')
            exit(1)

        merge_command(merge_with_squash, git_repo, github_repo, args['number'][0], merge_config)


if __name__ == '__main__':
    run()
