# git-pr-linear-merge

A command line utility to list and merge GitHub pull requests while maintaining linear history.

To maintain linear history, a pull request branch is rebased on top of its base, before merging. This creates a linear history like in this diagram:

<img width="350" alt="linear_history" src="https://user-images.githubusercontent.com/464795/115330193-947c3600-a161-11eb-9e2b-888fa04f7e34.png">

**Further Reading & Context**
- [A Tidy Linear Git History](https://www.bitsnbites.eu/a-tidy-linear-git-history/)
- [Avoid Messy Git History](https://dev.to/bladesensei/avoid-messy-git-history-3g26)
- [A Git Workflow for Agile Teams](http://reinh.com/blog/2009/03/02/a-git-workflow-for-agile-teams.html)
- [Git Rebase Tutorial](https://www.atlassian.com/git/tutorials/rewriting-history/git-rebase)

# Usage

## Installing

Python3.6 or above is required. You can install this package by running the following command:
```
pip3 install git-pr-linear-merge
```

To upgrade to the latest version:
```
pip3 install --upgrade git-pr-linear-merge
```

## How To Use

Get help: `git pr -h`

The first time you run this script, you will be asked to authenticate with Github.

List all open pull requests: `git pr list`, or list only yours with `git pr list --mine`
```
   #  Title                                                         Branch
----  ------------------------------------------------------------  -------------------------------
5811  Fix various bugs with video player                            fix/kevin-video-player-bugs
5812  Fix highlight being stuck when gallery frame is deactivated   fix/kevin-highlightable-view
...
```

Merge a pull request: `git pr merge NUMBER`
```
$ git pr merge 5850
| Preparing to merge Pull Request #5850
| Fetching
| Stashing local changes
| Checking out fix/room-template-state-refactor
| Updating fix/room-template-state-refactor
| Creating a backup branch before rebasing: backup/fix/room-template-state-refactor-11-05-36
| Updating dev
| Rebasing fix/room-template-state-refactor onto dev
| Force-pushing fix/room-template-state-refactor
| Checking out dev
| Updating dev
| Merging fix/room-template-state-refactor into dev
| Confirm merge:
  *   Merge: Room template state refactor (#5850) (HEAD -> dev)
  |\
  | * Don't allow users to save templates with too many items (origin/fix/room-template-state-refactor, fix/room-template-state-refactor)
  | * Use dictionary-id pattern to allow for any number of template loads at a time
  | * Use a dictionary-based state approach for room template loading
  |/
  * Undo changes to app id for Android, iPhone in a1e1c7 (origin/dev, origin/HEAD)
Does this look correct? (y/n) y
| Pushing dev
| Successfully merged Pull Request #5850
| Deleting the pull request branch fix/room-template-state-refactor
| Deleting the local backup branch backup/fix/room-template-state-refactor-11-05-36
| Checking out original branch fix/room-template-state-refactor
| Re-applying stashed changes
```

# Development

This section explains how to setup the dev environment and update the package

## Environment setup

```
python3 -m pip install virtualenv
python3 virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running Locally

With the environment setup through the previous step, you can run `git pr` using your local code by running the `git-pr.py` script in the root directory of this repo.
```
python3 git-pr.py
```

## Updating the package

Make sure to bump the version number with updates according to [PEP 440](https://www.python.org/dev/peps/pep-0440/)

### Publish and Install from TestPyPi

Before publishing for real, you can test a package by publishing it to TestPyPi

Publishing:
```
source venv/bin/activate
rm -rf dist
rm -rf build
python -m build
twine upload --repository testpypi dist/*
```

Installing:
```
python3 -m pip install --index-url https://test.pypi.org/simple/ git-pr-linear-merge
```

### Publish

```
source venv/bin/activate
rm -rf dist
rm -rf build
python -m build
twine upload dist/*
```