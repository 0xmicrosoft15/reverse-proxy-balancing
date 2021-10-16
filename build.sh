#!/usr/bin/env bash
##############################################################################################
# Quick Docker build script for Jussi. Builds Jussi as a docker container.
#
# By default, the image will be tagged as 'hive/jussi:TAG' - where 'TAG' is the current
# Git branch / tag. 
# If 'master' is checked out, then TAG will be changed to 'latest'.
#
# You can override the Docker image tag like so:
# 
#   # These will both simply tag the image as 'jussi' - no user/org, and no version tag
#   # (the version tag would default to :latest)
#   ./build.sh jussi
#   DK_TAG_FULL=jussi ./build.sh
#
#   # This will tag the image as 'someguy123/jussi:v1.2.3'
#   IMAGE_USER="someguy123" IMAGE_TAG="v1.2.3" ./build.sh
#
#   # This will tag the image as 'example/my-jussi:TAG' - where TAG will be 
#   # automatically determined from the git branch/tag.
#   REPO_NAME="my-jussi" IMAGE_USER="example" ./build.sh
#
#   # You can override the entire USER/REPO portion of the tag by setting IMAGE_REPO_NAME
#   # This would tag the image as 'jollypirate/custom-jussi:TAG' (TAG from git branch/tag)
#   IMAGE_REPO_NAME="jollypirate/custom-jussi" ./build.sh
#
##############################################################################################

# This variable detects the folder containing this script, allowing us to reference the containing folder,
# making it possible to run build.sh from any other folder, without causing path issues.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Build started on $(date)"

# Enter the folder containing this script
cd "$DIR"

: ${IMAGE_USER="hive"}

[ -z ${IMAGE_TAG+x} ] && IMAGE_TAG=`git ls-remote --heads origin | grep $(git rev-parse HEAD) | cut -d / -f 3`
if [ "$IMAGE_TAG" = "master" ] ; then export IMAGE_TAG=latest ; fi
[ -z ${REPO_PATH+x} ] && REPO_PATH=`git rev-parse --show-toplevel`
[ -z ${REPO_NAME+x} ] && REPO_NAME=`basename $REPO_PATH`
: ${IMAGE_REPO_NAME="${IMAGE_USER}/${REPO_NAME}"}
SOURCE_COMMIT=`git rev-parse HEAD`


if (( $# > 0 )); then
    echo -e "\nUsing docker tag specified as first argument: $1 \n"
    DK_TAG_FULL="$1"
fi

: ${DK_TAG_FULL="${IMAGE_REPO_NAME}:${IMAGE_TAG}"}

export IMAGE_USER IMAGE_TAG REPO_PATH REPO_NAME IMAGE_REPO_NAME SOURCE_COMMIT DK_TAG_FULL

echo "Building branch $IMAGE_TAG as docker image $DK_TAG_FULL"
docker build . -t "$DK_TAG_FULL" --build-arg SOURCE_COMMIT="${SOURCE_COMMIT}" --build-arg DOCKER_TAG="${IMAGE_TAG}"

# Return to the CWD the user was in prior to running this script.
cd - &> /dev/null

