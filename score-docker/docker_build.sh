#!/usr/bin/env bash

DOCKER_HOME=$(pwd)

DOCKER_BUILD_DIR=${DOCKER_HOME}/build
echo ${DOCKER_BUILD_DIR}
cd ..

rm dist/*

python setup.py sdist
python setup.py bdist_wheel

cd ${DOCKER_BUILD_DIR}

rm -f *.whl

cp ../../dist/*.whl .
WHEEL_FILE=$(ls *.whl)

sed "s/WHEEL_FILE/${WHEEL_FILE}/" Dockerfile.in > Dockerfile

docker build -t score_behavior . && docker tag score_behavior memdynlab/score:latest




