# Contributing to NetSentinel

Thank you for your interest in contributing to NetSentinel! This document provides guidelines and instructions for contributing.

## Table of Contents
1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Code Standards](#code-standards)
5. [Testing Requirements](#testing-requirements)
6. [Documentation](#documentation)
7. [Pull Request Process](#pull-request-process)
8. [Areas for Contribution](#areas-for-contribution)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender, gender identity, sexual orientation, disability, personal appearance, race, ethnicity, age, religion, or nationality.

### Expected Behavior

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Give constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or inflammatory comments
- Personal attacks
- Publishing others' private information
- Other conduct that would be inappropriate in a professional setting

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git
- Basic knowledge of the codebase

### Initial Setup

1. **Fork the Repository**
   ```bash
   # Navigate to the NetSentinel repository on GitHub
   # Click "Fork" button
   ```

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR-USERNAME/netsentinel.git
   cd netsentinel
   ```

3. **Add Upstream Remote**
   ```bash
   git remote add upstream https://github.com/original-org/netsentinel.git
   ```

4. **Setup Development Environment**
   ```bash
   # Backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Frontend
   cd netsentinel-ui
   npm install
   cd ..
   ```

5. **Start Services**
   ```bash
   docker-compose up -d
   ```

For detailed setup instructions, see [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).

---

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates
- `test/*` - Test updates

### Creating a Feature Branch

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes
git add .
git commit -m "feat: Add feature description"

# Push to your fork
git push origin feature/your-feature-name
```

### Keeping Your Branch Updated

```bash
# Fetch latest changes
git fetch upstream

# Rebase your branch on upstream/main
git checkout feature/your-feature-name
git rebase upstream/main

# Resolve conflicts if any
# Force push (only to your fork)
git push origin feature/your-feature-name --force-with-lease
```

---

## Code Standards

### Python Code Style

Follow [PEP 8](https://pep8.org/) style guide.

**Required Tools**:
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

**Setup**:
```bash
pip install black isort flake8 mypy
```

**Usage**:
```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .

# Type check
mypy .
```

**Configuration**: See `pyproject.toml` for detailed configuration.

### TypeScript/JavaScript Code Style

Follow standard JavaScript/TypeScript conventions.

**Required Tools**:
- **ESLint**: Linting
- **Prettier**: Code formatting (optional)

**Usage**:
```bash
cd netsentinel-ui

# Lint
npm run lint

# Auto-fix
npm run lint -- --fix

# Type check
npm run check
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes
- `perf`: Performance improvements
- `ci`: CI configuration changes

**Examples**:
```
feat(ml): Add FastFlow model integration

Implement FastFlow anomaly detection model with training
and inference capabilities.

Closes #123

---

fix(api): Resolve timeout issues in threat API

Reduce API response time by optimizing database queries
and implementing caching.

Fixes #456

---

docs: Update API documentation

Add missing endpoints and improve examples.

---

refactor(processor): Optimize event processing

Improve memory usage and processing speed by using
deque with maxlen and implementing batch processing.
```

---

## Testing Requirements

### Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=netsentinel --cov-report=html

# Run specific test file
pytest tests/test_event_analyzer.py

# Run integration tests
pytest -m integration
```

**Requirements**:
- All tests must pass
- Maintain 80%+ code coverage
- Add tests for new features
- Update tests for bug fixes

### Frontend Testing

```bash
cd netsentinel-ui

# Unit tests
npm test

# E2E tests
npm run test:e2e

# Coverage
npm run test:coverage
```

**Requirements**:
- All tests must pass
- Maintain 80%+ code coverage
- Add tests for new components
- Test accessibility

### Writing Tests

**Backend Example**:
```python
import pytest
from netsentinel.processors.event_analyzer import EventAnalyzer

@pytest.mark.asyncio
async def test_threat_detection():
    """Test threat detection algorithm."""
    analyzer = EventAnalyzer()
    await analyzer.start()
    
    event = create_test_event()
    result = await analyzer.analyze_event(event)
    
    assert result.threat_score >= 0
    assert result.threat_score <= 10
    assert result.threat_level is not None
    
    await analyzer.stop()
```

**Frontend Example**:
```typescript
import { render, screen } from '@testing-library/react';
import { StatCard } from '@/components/StatCard';

describe('StatCard', () => {
  it('renders with correct props', () => {
    render(<StatCard title="Test" value={100} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });
});
```

---

## Documentation

### Updating Documentation

Documentation is part of the codebase and should be updated alongside code changes.

**Documentation Files**:
- API: `docs/API.md`
- Deployment: `docs/DEPLOYMENT.md`
- Developer: `docs/DEVELOPER_GUIDE.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
- Index: `docs/DOCUMENTATION_INDEX.md`

**Documentation Guidelines**:
- Write clear, concise documentation
- Include code examples
- Keep examples up-to-date
- Use correct markdown formatting
- Add diagrams when helpful

**When to Update**:
- Adding new features
- Fixing bugs
- Changing API endpoints
- Updating configuration
- Adding new integrations

---

## Pull Request Process

### Before Submitting

- [ ] Code follows style guides
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] Branch is up-to-date with upstream/main
- [ ] No merge conflicts

### Pull Request Checklist

```markdown
- [ ] Code follows style guides
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Comments added for complex code
- [ ] No console.log statements (use logging)
- [ ] Type hints added (Python)
- [ ] Types added (TypeScript)
- [ ] Breaking changes documented
- [ ] Migration guide added (if needed)
```

### Submitting Pull Request

1. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Navigate to your fork on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out PR template

3. **PR Description Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   Describe tests performed
   
   ## Checklist
   - [ ] Code follows style guides
   - [ ] All tests pass
   - [ ] Documentation updated
   
   ## Related Issues
   Closes #123
   
   ## Screenshots (if applicable)
   Add screenshots for UI changes
   ```

4. **Review Process**
   - PR will be reviewed by maintainers
   - Address any feedback
   - Update PR as needed
   - Maintainers will merge when approved

---

## Areas for Contribution

### High Priority 🔴

#### Backend
- **ML Integration**: Complete Anomalib model integration
  - Full inference implementation
  - Model versioning
  - Training pipeline automation
- **Real-time Updates**: WebSocket implementation
- **Authentication**: OAuth/JWT implementation
- **Testing**: Increase test coverage

#### Frontend
- **Backend Integration**: Replace mock services with real APIs
- **Real-time Updates**: WebSocket integration
- **Authentication**: Real OAuth/JWT flows
- **Performance**: Optimization and caching

### Medium Priority 🟡

#### Backend
- **SIEM Connectors**: Additional integrations (QRadar, ArcSight)
- **SDN Controllers**: Support for more controllers
- **Performance**: Caching and optimization
- **Security**: Security audits and improvements

#### Frontend
- **Advanced Features**: RBAC, multi-tenancy
- **UI Enhancements**: Additional features
- **Testing**: E2E test coverage
- **Documentation**: User guides and tutorials

### Low Priority 🟢

#### Backend
- **Internationalization**: Multi-language support
- **Additional Services**: More honeypot modules
- **Analytics**: Advanced analytics features
- **Examples**: Code examples and demos

#### Frontend
- **Accessibility**: WCAG AAA compliance
- **Internationalization**: Multi-language UI
- **Themes**: Additional theme options
- **Customization**: User customization features

---

## Getting Help

### Resources

- **Documentation**: See `docs/` directory
- **Issues**: Search existing issues
- **Discussions**: Join GitHub discussions
- **Code Comments**: Read inline documentation

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and discussions
- **Pull Requests**: Code review feedback
- **Email**: For sensitive issues

### Before Asking

1. Search existing issues/discussions
2. Read relevant documentation
3. Check code comments
4. Reproduce the issue
5. Prepare information for report

---

## Recognition

Contributors will be recognized:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Acknowledged in documentation
- Invited to maintainer team (for significant contributions)

---

## License

By contributing to NetSentinel, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to NetSentinel! 🎉

Your contributions help make NetSentinel better for everyone.

**Questions?** Open an issue or join a discussion on GitHub.

