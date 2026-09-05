# Contributing to OFO-DBMS

First off — thank you for taking the time to contribute! 🎉

This document explains how to set up your environment, make changes, and submit a pull request.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Branching Strategy](#branching-strategy)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Running Tests](#running-tests)

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

---

## How to Contribute

You can contribute by:

- 🐛 **Reporting bugs** — Open an [issue](../../issues/new?template=bug_report.md)
- 💡 **Suggesting features** — Open an [issue](../../issues/new?template=feature_request.md)
- 🔧 **Fixing bugs or adding features** — Fork the repo, make changes, and open a Pull Request
- 📝 **Improving documentation** — Fix typos, add examples, clarify explanations
- ✅ **Writing tests** — Improve test coverage for any app

---

## Development Setup

### 1. Fork & Clone

`bash
# Fork via GitHub UI, then:
git clone https://github.com/YOUR_USERNAME/OFO-DBMS.git
cd OFO-DBMS
`

### 2. Set Up Virtual Environment

`bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
`

### 3. Install Dependencies

`bash
pip install -r requirements.txt
`

### 4. Configure Environment

`bash
cp .env.example .env
# Edit .env and fill in your DJANGO_SECRET_KEY
`

### 5. Apply Migrations & Run

`bash
python manage.py migrate
python manage.py migrate --database=django_database
python manage.py createsuperuser
python manage.py runserver
`

---

## Branching Strategy

We use a simple feature branch workflow:

| Branch | Purpose |
|---|---|
| main | Stable, production-ready code |
| feature/<name> | New feature development |
| fix/<name> | Bug fixes |
| docs/<name> | Documentation-only changes |
| chore/<name> | Maintenance tasks (deps, config) |

**Always branch off main:**

`bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
`

---

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

`
<type>(<scope>): <short description>

[optional body]

[optional footer]
`

### Types

| Type | When to use |
|---|---|
| feat | A new feature |
| fix | A bug fix |
| docs | Documentation only |
| style | Formatting (no logic change) |
| refactor | Code restructure (no feature/bug change) |
| test | Adding or updating tests |
| chore | Build process, dependency updates |

### Examples

`
feat(orders): add order cancellation within 5 minutes of placement
fix(cart): resolve quantity going negative on decrement
docs(readme): add environment variable table
test(accounts): add tests for profile update view
`

---

## Pull Request Process

1. **Ensure tests pass** before submitting:
   `bash
   python run_tests.py
   `

2. **Update documentation** if your change affects user-facing behavior or adds new models/views.

3. **Fill out the PR template** completely. PRs with missing sections may be closed.

4. **One PR = one concern.** Keep changes focused. Large PRs are harder to review.

5. **Wait for review.** A maintainer will review and may request changes.

6. Once approved, a maintainer will **squash-merge** the PR into main.

---

## Code Style

- Follow **PEP 8** for Python code
- Use **Django's coding style** for models, views, and URL patterns
- Keep views thin — heavy business logic should live in model methods or service functions
- All new views must have a docstring explaining their purpose
- Use get_object_or_404 rather than raw .get() to handle missing records gracefully
- Write tests for every new view or model method you add

### Template Style
- Use Bootstrap 5 utility classes
- Keep template logic minimal — move complex logic to views or template tags
- Use {% block %} and {% extends 'base.html' %} for all templates

---

## Running Tests

`bash
# Run all tests
python run_tests.py

# Run tests for a specific app
python manage.py test accounts --verbosity=2
python manage.py test restaurants --verbosity=2
python manage.py test orders --verbosity=2
`

---

Thank you for contributing to OFO-DBMS! 🍽️
