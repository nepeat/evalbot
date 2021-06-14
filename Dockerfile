FROM alpine:edge

RUN apk add --no-cache openssl zsh python3 py3-pip \
    && pip3 install bottom

WORKDIR /evalbot
ADD . /evalbot

CMD ["zsh","evalbot.sh","irc.tilde.chat:6697","evalbot","#chaos"]
