# Contributions Guide

Thank you for considering contributing to our AWS CloudFormation Stack project! We are excited to work with you to improve this stack and make it more useful for the community. This guide outlines the contribution process and standards.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Contribute](#how-to-contribute)
   - [Bug Reports and Feature Requests](#bug-reports-and-feature-requests)
   - [Pull Requests](#pull-requests)
3. [Development Workflow](#development-workflow)
4. [Style Guide](#style-guide)
   - [YAML Guidelines](#yaml-guidelines)
   - [Documentation Standards](#documentation-standards)
5. [License](#license)

---

## Code of Conduct

Please review and follow our [Code of Conduct](CODE_OF_CONDUCT.md). All participants are expected to foster a welcoming and inclusive community.

---

## How to Contribute

We welcome contributions in the following areas:

- Reporting bugs
- Suggesting features
- Adding new templates or enhancements
- Improving documentation
- Reviewing pull requests

### Bug Reports and Feature Requests

1. **Search Existing Issues**: Check if the bug or feature request already exists in the [Issues tab](https://github.com/MemVerge/mv-spot-viewer/issues).
2. **Create a New Issue**: If not found, open a new issue with:
   - A clear title
   - A detailed description
   - Steps to reproduce the issue (if applicable)
   - Suggested improvements or desired outcomes for feature requests

### Pull Requests

1. **Fork and Clone**: Fork the repository and clone your fork:
   ```bash
   git clone https://github.com/MemVerge/mv-spot-viewer.git
   cd your-repo
   ```
2. **Branch Creation**: Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit and Push**: Write descriptive commit messages and push your branch:
   ```bash
   git commit -m "Add feature for X"
   git push origin feature/your-feature-name
   ```
4. **Open A Pull Request**: Submit your changes to the main branch, linking any relevant issues.


Style Guide

YAML Guidelines
	•	Use 2 spaces for indentation.
	•	Avoid trailing whitespace.
	•	Follow AWS CloudFormation best practices for template design:
	•	Use Parameters and Mappings for flexibility.
	•	Use Outputs for key resources.
	•	Add descriptions to all Resources.

Documentation Standards
	•	Document all parameters, outputs, and resource descriptions in the template.
	•	Update the README file to include:
	•	Instructions for deploying the stack.
	•	Configuration examples.
	•	Common troubleshooting tips.

 We appreciate your contributions and look forward to collaborating with you. If you have questions, feel free to reach out via the Issues tab or open a discussion.