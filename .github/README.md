# NetSentinel GitHub Workflows

This directory contains GitHub Actions workflows for continuous integration, testing, building, and deployment of NetSentinel.

## Available Workflows

### 🔄 CI/CD Pipeline (`ci.yml`)
**Triggers**: Push/PR to main/develop branches
**Purpose**: Complete CI/CD pipeline with multiple stages

**Jobs Included**:
- **Pre-commit Checks**: Code formatting and linting
- **Code Quality**: Type checking (mypy), linting (pylint), security scans (bandit)
- **Unit Tests**: Core functionality tests across Python versions
- **Integration Tests**: Service integration with Kafka, Redis, etc.
- **Docker Integration Tests**: Full stack testing with Docker Compose
- **Security Tests**: Vulnerability scanning and dependency checks
- **Performance Tests**: Load testing and performance metrics
- **ML Tests**: Anomaly detection model validation
- **Smoke Tests**: Basic functionality verification
- **Test Report**: Comprehensive results summary
- **Staging Deployment**: Automated deployment on main branch success

### 🧪 Comprehensive Testing (`comprehensive-tests.yml`)
**Triggers**: Push/PR to main/develop branches, manual dispatch
**Purpose**: Focused comprehensive testing using our custom test suite

**Features**:
- **Multiple Test Modes**:
  - `full`: Complete test suite (default)
  - `quick`: Infrastructure + core functionality only
  - `components-only`: Individual component tests
- **Docker Integration**: Full stack testing with service orchestration
- **Test Orchestration**: Uses our `run_all_tests.ps1` script
- **Security Scanning**: Bandit and Safety scans
- **Artifact Collection**: Test results, logs, and summaries

### 📦 Docker Build (`docker-build.yml`)
**Triggers**: Push to main, releases, manual dispatch
**Purpose**: Multi-platform Docker image building and publishing

**Features**:
- **Multi-architecture**: Linux AMD64 and ARM64 builds
- **Docker Hub Publishing**: Automated image publishing
- **Metadata Tagging**: Semantic versioning and branch-based tags
- **Build Caching**: GitHub Actions cache for faster builds

### 🚀 PyPI Publishing (`publish.yml`)
**Triggers**: GitHub releases
**Purpose**: Automated package publishing to PyPI

**Features**:
- **Trusted Publishing**: Uses PyPI's trusted publisher mechanism
- **Version Validation**: Ensures package version matches release tag
- **Build Verification**: Tests package installation before publishing

### 🧹 Stale Issue Management (`stale_issues.yml`)
**Triggers**: Daily cron schedule
**Purpose**: Automated management of inactive issues and PRs

**Configuration**:
- **Issue Stale Time**: 14 days of inactivity
- **Issue Close Time**: 14 days after marking as stale
- **PR Handling**: PRs are not auto-closed (only issues)
- **Exemptions**: Issues/PRs with "exempt" label are preserved

### 📝 NetSentinel Tests (`netsentinel_tests.yml`)
**Triggers**: Push/PR to main/develop branches
**Purpose**: Package build and basic functionality testing

**Features**:
- **Multi-Python Support**: Tests across Python 3.11 and 3.12
- **Package Building**: Validates package can be built and installed
- **Import Testing**: Verifies all core modules can be imported
- **Basic Functionality**: Smoke tests for core components

## Workflow Architecture

### Testing Strategy
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Quick Tests   │ -> │ Component Tests │ -> │Integration Tests│
│                 │    │                 │    │                 │
│ • Infrastructure │    │ • Database      │    │ • Full Stack    │
│ • Core APIs     │    │ • Firewall      │    │ • End-to-End    │
└─────────────────┘    │ • Alerting      │    └─────────────────┘
                       │ • SDN           │
                       └─────────────────┘
```

### CI/CD Stages
1. **Code Quality**: Linting, type checking, security scans
2. **Unit Testing**: Isolated component testing
3. **Integration Testing**: Service interaction testing
4. **Docker Testing**: Full environment validation
5. **Security Testing**: Vulnerability assessment
6. **Performance Testing**: Load and performance validation
7. **Deployment**: Automated staging deployment

## Configuration

### Required Secrets
- `DOCKERHUB_USERNAME`: Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token
- `GITHUB_TOKEN`: Automatically provided by GitHub

### Environment Variables
- `PYTHON_VERSION`: Python version for testing (default: "3.11")

### Service Dependencies
The integration tests require the following services:
- **Redis**: Port 6379
- **Kafka**: Port 9092 (with Zookeeper on 2181)
- **Elasticsearch**: Port 9200
- **InfluxDB**: Port 8086

## Usage Examples

### Running Tests Locally
```bash
# Quick infrastructure check
pwsh scripts/test-netsentinel-docker.ps1

# Full functionality test
pwsh scripts/test_functionality.ps1

# Complete test suite
pwsh scripts/run_all_tests.ps1
```

### Triggering Workflows
- **Automatic**: Push to main/develop branches
- **Manual**: Use "Run workflow" button in GitHub Actions
- **Release**: Create a GitHub release

### Monitoring Results
- **Test Reports**: Available as workflow artifacts
- **Logs**: Detailed logs in each workflow run
- **Coverage**: Codecov integration for unit test coverage
- **Security**: Automated security scan results

## Troubleshooting

### Common Issues

**Workflow Permissions**:
- Ensure repository has Actions enabled
- Check that required secrets are configured

**Docker Build Issues**:
- Verify Dockerfile paths are correct
- Check build context and file references

**Test Failures**:
- Review test logs for specific error messages
- Check if external services (Redis, Kafka) are running
- Verify environment variables are set correctly

**Security Scan Failures**:
- Review Bandit/Safety output for specific vulnerabilities
- Update dependencies or add security exemptions as needed

## Development

### Adding New Workflows
1. Create workflow file in `.github/workflows/`
2. Follow naming convention: `component-action.yml`
3. Include proper triggers and permissions
4. Add documentation to this README

### Modifying Existing Workflows
1. Update the workflow YAML file
2. Test changes on a feature branch
3. Update this documentation
4. Ensure backward compatibility

## Support

For workflow-related issues:
1. Check GitHub Actions logs for detailed error messages
2. Review workflow configuration for syntax errors
3. Test workflows on feature branches before merging
4. Create issues for workflow improvements or bug fixes
