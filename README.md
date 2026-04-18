Git Workflow
slm_repo
main is the stable, trainable branch.
feature/* branches are used for development and experiments.
Training runs are launched from an exact git commit hash, not from whatever branch happens to be checked out on M3.
Code is developed on the Surface Pro, committed, and pushed before launching through TAP.
tap
main is the stable deployed version of TAP.
feature/* branches are used for new TAP features.
After pulling new TAP changes on the MacBook, the Docker container should be rebuilt.
Launch Rule

Before launching a training run:

Commit changes in slm_repo
Push to GitHub
Get the commit hash with git rev-parse HEAD
Send that commit hash to TAP in the launch request
Why

This keeps runs reproducible and avoids launching from uncommitted or ambiguous code states.