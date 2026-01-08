#!/bin/bash
# Mises à jour de sécurité

pip list --outdated
pip install --upgrade flask flask-login werkz
