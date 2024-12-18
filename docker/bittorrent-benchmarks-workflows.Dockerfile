FROM bitnami/kubectl:1.31.1 as kubectl

FROM debian:bookworm-slim

COPY --from=kubectl /opt/bitnami/kubectl/bin/kubectl /usr/local/bin/kubectl

RUN apt-get update && apt-get install -y curl

RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
RUN chmod 700 get_helm.sh
RUN ./get_helm.sh

RUN mkdir /opt/bittorrent-benchmarks
WORKDIR /opt/bittorrent-benchmarks
COPY ./k8s ./k8s
COPY ./docker ./docker
