# Get the current working directory
current_dir=$(pwd)

# Configure git for the current directory
git config --global --add safe.directory $current_dir

# Traverse all sub-directories in third-party
for dir in ./third_party/*/
do
  # Remove trailing slash
  dir=${dir%*/}
  echo $current_dir/$dir
  # Execute git config for each sub-directory
  git config --global --add safe.directory $current_dir/$dir
done