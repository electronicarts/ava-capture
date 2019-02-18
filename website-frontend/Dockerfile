FROM node:6.13

WORKDIR /build

ADD package.json /build

RUN npm install
RUN npm rebuild node-sass

ADD src /build/src/
ADD config /build/config/
ADD webpack.config.js /build
ADD tsconfig.json /build

ENTRYPOINT npm run build:dev
