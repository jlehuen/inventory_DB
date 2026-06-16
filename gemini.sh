#!/bin/bash

# git config --global --unset http.proxy
# brew update
# brew cleanup
# brew upgrade gemini-cli
# gemini --version

export HTTP_PROXY="http://proxy.univ-lemans.fr:3128" 
gemini
