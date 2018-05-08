#!/bin/bash

main() {
  git add -A
  git status
  git commit -v -m "$@"
  git push -u origin master
}

if [[ -n "$@" ]]; then
  main "$@"
else
  main "Version bump"
fi