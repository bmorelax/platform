#!/usr/bin/env bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}

NAME=platform
USER=www-data

if [ ! -f uwsgi/uwsgi.tar.gz ]; then
  ./uwsgi/build.sh
else
  echo "skipping uwsgi build"
fi

if [ ! -f nginx/nginx.tar.gz ]; then
  ./nginx/build.sh
else
  echo "skipping nginx build"
fi

rm -rf build
mkdir -p build/${NAME}

cp -r bin build/${NAME}
cp -r config build/${NAME}
cp -r www build/${NAME}
cp -r socket build/${NAME}
chown -R ${USER}. build/${NAME}/socket

tar xzf nginx/nginx.tar.gz -C build/${NAME}
tar xzf nginx/uwsgi.tar.gz -C build/${NAME}
rm -rf ${NAME}.tar.gz
tar cpzf ${NAME}.tar.gz -C build/ ${NAME}

echo "app: ${NAME}.tar.gz"