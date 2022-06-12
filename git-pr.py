import sys
import os

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(DIR_PATH, 'src'))

from git_pr_linear_merge.main import run
if __name__ == '__main__':
    run()