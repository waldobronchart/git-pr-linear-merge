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

**Installing**

Python3.6 or above is required. You can install this package by running the following command:
```
pip3 install git-pr-linear-merge
```

**How To Use**

```
git pr -h
git pr list
git pr merge NUMBER
```

The first time you run this, you will be asked to authenticate with Github.



# Development

This section explains how to setup the dev environment and update the package

## Environment setup

```
python3 -m pip install virtualenv
python3 virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Running Locally**

With the environment setup through the previous step, you can run `git pr` using your local code by running the `git-pr.py` script in the root directory of this repo.
```
python3 git-pr.py
```

## Updating the package

Make sure to bump the version number with updates according to [PEP 440](https://www.python.org/dev/peps/pep-0440/)

**Test Publish**
```
source venv/bin/activate
rm -rf dist
rm -rf build
python -m build
twine upload --repository testpypi dist/*
```

**Publish**
```
source venv/bin/activate
rm -rf dist
rm -rf build
python -m build
twine upload dist/*
```