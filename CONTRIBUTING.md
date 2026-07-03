# Contributing Guidelines

Thank you for your interest in contributing to AWS Cost Anomaly Detective!

## How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-new-feature`
3. **Make your changes**
4. **Test your changes**: Ensure all tests pass
5. **Commit**: Use clear, descriptive commit messages
6. **Push**: `git push origin feature/my-new-feature`
7. **Open a Pull Request**

## Code Style

- Follow PEP 8 for Python code
- Use type hints
- Add docstrings for all functions
- Keep functions focused and testable

## Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## Reporting Bugs

Open an issue with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, AWS region, etc.)

## Feature Requests

We welcome feature requests! Open an issue with:
- Use case description
- Proposed solution
- Any alternative approaches considered

## Security Issues

**Do not open public issues for security vulnerabilities.**

Email: aws-security@amazon.com

## Code of Conduct

This project adheres to the [AWS Code of Conduct](https://aws.github.io/code-of-conduct).

## License

By contributing, you agree that your contributions will be licensed under the MIT-0 License.
