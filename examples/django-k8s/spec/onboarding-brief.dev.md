# Example Onboarding Brief — Django on Kubernetes (dev)

## Goal
Deploy a Django application from GitHub to Kubernetes in a dev environment.

## Application
- Framework: Django
- Port: 8000
- Repo: example-org/example-django
- Branch: main

## Platform
- Kubernetes namespace: example-dev
- Ingress: enabled

## CI/CD
- Build container image on push to main
- Deploy automatically to dev
- Run Django migrations on deploy