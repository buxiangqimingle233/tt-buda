# Get the current working directory
current_dir=$(pwd)

# Configure git for the current directory
git config --global --add safe.directory $current_dir

# Traverse all sub-directories in third-party recursively
find ./third_party -type d | while read dir
do
  # Remove the ./ from the dir variable

  # Check if the directory contains a .git directory
  if [ -d "$dir/.github" -o -d "$dir/.git" ]; then
    dir=$(echo $dir | sed 's|./||')
    echo  $current_dir/$dir
    # Execute git config for each sub-directory
    git config --global --add safe.directory $current_dir/$dir
  fi
done