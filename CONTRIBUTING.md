# Contributing to K9LogBot

We love your input! We want to make contributing to K9LogBot as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Requests

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Any Contributions You Make Will Be Under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](LICENSE) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report Bugs Using GitHub's [Issue Tracker](https://github.com/PR0M4XIMUS/k9LogBot/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/PR0M4XIMUS/k9LogBot/issues/new).

## Write Bug Reports with Detail, Background, and Sample Code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Development Environment Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/k9LogBot.git
cd k9LogBot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your bot token and chat ID
```

## Code Style

- Use Python 3.11+ features where appropriate
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular

## Testing Your Changes

Before submitting a pull request:

1. **Test with Docker:**
   ```bash
   docker-compose up -d --build
   docker-compose logs -f
   ```

2. **Run deployment tests:**
   ```bash
   ./test_deployment.sh
   ```

3. **Test bot functionality:**
   - Send `/start` to your bot
   - Test walk logging with `/addwalk`
   - Verify balance with `/balance`
   - Test admin functions if applicable

4. **Check OLED display** (if connected):
   - Verify display shows current stats
   - Test notifications work

## Feature Requests

Feature requests are welcome! Please open an issue with:
- Clear description of the feature
- Use cases and benefits
- Potential implementation approach (if you have ideas)

## Areas Where We'd Love Help

- **Additional display types** - Support for different OLED/LCD displays
- **Currency support** - Support for other currencies besides MDL  
- **Mobile app** - React Native or Flutter companion app
- **Web dashboard** - Web interface for statistics and management
- **Docker optimization** - Further container size and performance improvements
- **Testing** - Unit tests and integration tests
- **Documentation** - More examples, tutorials, and use cases

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

## References

This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/main/CONTRIBUTING.md).