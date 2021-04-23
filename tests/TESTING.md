# Testing Script

This is a long checklist of things to test manually. Placeholder for real tests.

- Auth
    - Fresh install, authentication not setup yet. Run the script and go through the auth setup flow. Before running this test, delete the `~/.linmergerc` file
        - [ ] enter nothing when asked
        - [ ] enter invalid token
        - [ ] enter valid token
    - [ ] Auth token through argument: `git pr list --token XXXX`
    - [ ] Invalid token set in rc file. Open `~/.linmergerc` and enter an invalid token in the file.
- Arguments
    - [ ] verbosity: `git pr list -v`
- List Command
    - [ ] functions properly: `git pr list`
    - [ ] list only my prs: `git pr list --mine`
- Merge Command
    - [ ] no pull request number specified: `git pr merge`
    - ...wip (there are a lot of edge cases here)
- Edge cases
    - [ ] run the script in a directory that is not a git repository
    - [ ] run the script in a directory that is not a Github-based git repository
