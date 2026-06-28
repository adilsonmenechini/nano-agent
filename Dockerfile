FROM alpine:3.19

ARG UID=1000
ARG GID=1000

RUN apk add --no-cache curl ca-certificates bash libstdc++ libgcc \
    && curl -fsSL https://opencode.ai/install | bash \
    && mv /root/.opencode/bin/opencode /usr/local/bin/opencode \
    && apk del curl

RUN addgroup -g $GID coder 2>/dev/null; \
    adduser -D -s /bin/sh -u $UID -G coder coder \
    && mkdir -p /home/coder/.config/opencode

USER coder
WORKDIR /workspace
CMD ["opencode"]
