# NetSentinel Content Migration Checklist

## 📋 **Content That Needs to Be Moved/Updated**

### **1. ✅ Already Moved to `src/`**
- ✅ **`anomalib/`** → `src/anomalib/`
- ✅ **`data/`** → `src/data/` (consolidated)
- ✅ **`hybrid-data/`** → `src/data/` (merged)
- ✅ **`netsentinel/`** → `src/netsentinel/`

### **2. 🔄 Files That Need Branding Updates**

#### **Build Scripts**
- [ ] **`build_scripts/build_opencanary.sh`** → Update to NetSentinel
- [ ] **`build_scripts/docker-hybrid-setup.sh`** → Update to NetSentinel
- [ ] **`build_scripts/start-hybrid.sh`** → Update to NetSentinel
- [ ] **`build_scripts/stop-hybrid.sh`** → Update to NetSentinel
- [ ] **`build_scripts/test-hybrid.sh`** → Update to NetSentinel

#### **Service Files**
- [ ] **`opencanary.service`** → Rename to `netsentinel.service` and update content

#### **Docker Files**
- [ ] **`Dockerfile`** → Update paths and references
- [ ] **`Dockerfile.event-processor`** → Update paths and references
- [ ] **`docker-compose.yml`** → Update service names and paths

#### **Kubernetes Manifests**
- [ ] **`k8s/netsentinel.yaml`** → Update image references and paths
- [ ] **`k8s/event-processor.yaml`** → Update paths
- [ ] **`k8s/kafka.yaml`** → Update paths
- [ ] **`k8s/redis.yaml`** → Update paths (was Valkey)

#### **Helm Charts**
- [ ] **`helm/netsentinel/Chart.yaml`** → Update metadata
- [ ] **`helm/netsentinel/values.yaml`** → Update values
- [ ] **`helm/netsentinel/templates/`** → Update templates

### **3. 📁 Missing Directories That Should Be Created**

#### **Integration Tests**
- [ ] **`tests/`** (root level) → Create for integration tests
- [ ] **`tests/integration/`** → Move integration tests here
- [ ] **`tests/unit/`** → Move unit tests here (if not in src/)

### **4. 🔧 Configuration Files That Need Updates**

#### **Docker Compose**
- [ ] **`docker-compose.yml`** → Update volume mounts for new paths:
  ```yaml
  volumes:
    - ./src/data/redis:/etc/redis
    - ./src/data/kafka:/etc/kafka
    - ./src/data/opencanary:/etc/opencanary
  ```

#### **Kubernetes**
- [ ] **`k8s/`** → Update all manifests for new directory structure
- [ ] **`helm/`** → Update Helm charts for new structure

#### **Scripts**
- [ ] **`scripts/`** → Update script paths and references
- [ ] **`scripts/train_ml_models.py`** → Update import paths

### **5. 📝 Documentation Updates**

#### **README Files**
- [ ] **`README.md`** → Update installation and usage instructions
- [ ] **`docs/`** → Update all documentation for new structure

#### **Configuration Guides**
- [ ] **`docs/`** → Update setup guides for new paths
- [ ] **`docs/`** → Update deployment guides

### **6. 🗂️ Files That Should Stay in Root**

#### **Configuration Files** (Keep in root)
- ✅ **`pyproject.toml`** → Already configured for src layout
- ✅ **`setup.py`** → Keep in root
- ✅ **`requirements.txt`** → Keep in root
- ✅ **`pytest.ini`** → Keep in root
- ✅ **`tox.ini`** → Keep in root
- ✅ **`.flake8`** → Keep in root

#### **Deployment Files** (Keep in root)
- ✅ **`k8s/`** → Keep in root
- ✅ **`helm/`** → Keep in root
- ✅ **`docker-compose.yml`** → Keep in root
- ✅ **`Dockerfile`** → Keep in root

#### **Documentation** (Keep in root)
- ✅ **`docs/`** → Keep in root
- ✅ **`README.md`** → Keep in root

#### **Scripts** (Keep in root)
- ✅ **`scripts/`** → Keep in root
- ✅ **`build_scripts/`** → Keep in root

## 🎯 **Priority Order**

### **High Priority (Immediate)**
1. **Update Docker Compose** for new paths
2. **Update Kubernetes manifests** for new structure
3. **Update service files** to NetSentinel branding
4. **Create missing tests directory** structure

### **Medium Priority**
1. **Update build scripts** to NetSentinel branding
2. **Update Helm charts** for new structure
3. **Update documentation** for new paths

### **Low Priority**
1. **Update script references** in documentation
2. **Update example configurations**
3. **Update CI/CD pipelines**

## 🚀 **Next Steps**

1. **Create missing directories**:
   ```bash
   mkdir -p tests/integration
   mkdir -p tests/unit
   ```

2. **Update Docker Compose**:
   ```yaml
   volumes:
     - ./src/data/redis:/etc/redis
     - ./src/data/kafka:/etc/kafka
     - ./src/data/opencanary:/etc/opencanary
   ```

3. **Update Kubernetes manifests** for new paths

4. **Update service files** to NetSentinel branding

5. **Update build scripts** to NetSentinel branding

---

*This checklist ensures all content is properly organized and updated for the new NetSentinel structure.*
