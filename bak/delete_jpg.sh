#!/usr/bin/env bash

# Define three path options
path1="/home/huai/data/Downloads/mv"
path2="/home/huai/data/Downloads/h"
path3="/home/huai/data/Downloads/whitenoise"

# Prompt user to select a path
echo "Please select the directory to delete .jpg files from:"
echo "1. $path1"
echo "2. $path2"
echo "3. $path3"
read -p "Enter option (1, 2, or 3): " choice

# Set deletion path based on user choice
case $choice in
1)
	delete_dir="$path1"
	;;
2)
	delete_dir="$path2"
	;;
3)
	delete_dir="$path3"
	;;
*)
	echo "Invalid input, please try again."
	exit 1
	;;
esac

# Find and delete all .jpg files in the specified directory and its subdirectories
find "$delete_dir" -type f -name "*.jpg" -delete

echo "Deletion complete."
