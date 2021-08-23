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

### List Command

List all open pull requests: `git pr list`, or list only yours with `git pr list --mine`
```
   #  Title                                                         Branch
----  ------------------------------------------------------------  -------------------------------
5811  Fix various bugs with video player                            fix/kevin-video-player-bugs
5812  Fix highlight being stuck when gallery frame is deactivated   fix/kevin-highlightable-view
...
```

### Merge Command

Merge a pull request: `git pr merge NUMBER`

![image](https://user-images.githubusercontent.com/464795/130376573-d7d6ea25-3b34-4b15-84df-1ca30cd94f89.png)

### Squash Command

Squash a pull request: `git pr squash NUMBER`

The squash command collapses all commits from the pull branch into a single commit and puts that commit straight onto the base branch without doing an explicit merge.

Here's what the history looks like when you use `squash` vs `merge`.

![image](https://user-images.githubusercontent.com/464795/130379156-1b6f19fd-075b-4899-92e9-29df49b0fb73.png)


## Repo configuration

Add a `.linmergerc` config file to the repo root directory to customize behaviour to your teams preference.

Below are all the options
```ini
[merge]
# Commit message format vars: TITLE, NUMBER, AUTHOR_NAME, AUTHOR_USERNAME
merge_msg_format = Merge: {TITLE} (#{NUMBER})
# Enable single-commit pulls to be squashed instead of merging, even when explicitly using the merge command
always_squash_single_commit_pulls = True

[squash]
squash_msg_format = {TITLE} (#{NUMBER})
# Enable usage of the `git pr squash` command
squash_cmd_enabled = True
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

## Running Locally

With the environment setup through the previous step, you can run `git pr` using your local code by running the `git-pr.py` script in the root directory of this repo.
```
python3 ~/path/to/your/local/checkout/git-pr.py
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
