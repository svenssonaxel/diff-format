FROM debian:bullseye

# Install dependencies
RUN apt-get update -y && apt-get install -y git imagemagick make python3 shellcheck texlive texlive-fonts-extra

# Allow ImageMagick to do whatever it pleases
RUN rm /etc/ImageMagick-*/policy.xml

# Create and use user
RUN useradd -m -s /bin/bash user
USER user

# Configure git
RUN git config --global user.email "dummy@localhost" && git config --global user.name "Dummy" && git config --global init.defaultBranch master
