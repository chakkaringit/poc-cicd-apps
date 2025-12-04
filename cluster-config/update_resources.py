import csv
import os
import yaml

# ================= CONFIGURATION =================
CSV_FILE = 'resources.csv'
APP_SOURCE_DIRS = [
    '../apps',
    '../database-services'
]
# =================================================

def format_cpu(val):
    val = str(val).strip()
    if not val: return None
    if val.isdigit(): return f"{val}m"
    return val

def format_mem(val):
    val = str(val).strip()
    if not val: return None
    if val.isdigit(): return f"{val}Mi"
    return val

def format_storage(val):
    val = str(val).strip()
    if not val: return None
    if val.isdigit(): return f"{val}Gi"
    return val

def update_yaml_file(file_path, cpu, ram, storage, service_name):
    try:
        with open(file_path, 'r') as f:
            documents = list(yaml.safe_load_all(f))
    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")
        return
    
    modified = False
    
    for doc in documents:
        if not doc: continue
        kind = doc.get('kind')

        # CASE 1: Workloads (Deployment, StatefulSet, etc.)
        if kind in ['Deployment', 'StatefulSet', 'DaemonSet']:
            try:
                containers = doc['spec']['template']['spec']['containers']
                for container in containers:
                    if 'resources' not in container: container['resources'] = {}
                    res = container['resources']
                    if 'requests' not in res: res['requests'] = {}
                    if 'limits' not in res: res['limits'] = {}
                    
                    if cpu:
                        res['requests']['cpu'] = cpu
                        res['limits']['cpu'] = cpu 
                    if ram:
                        res['requests']['memory'] = ram
                        res['limits']['memory'] = ram
                        
                    modified = True
                
                # Update StatefulSet Volume Templates
                if kind == 'StatefulSet' and storage and 'volumeClaimTemplates' in doc['spec']:
                    for vct in doc['spec']['volumeClaimTemplates']:
                        if 'resources' not in vct['spec']: vct['spec']['resources'] = {}
                        if 'requests' not in vct['spec']['resources']: vct['spec']['resources']['requests'] = {}
                        
                        vct['spec']['resources']['requests']['storage'] = storage
                        modified = True
                        print(f"   -> Updated StatefulSet storage to {storage}")

            except KeyError:
                pass

        # CASE 2: PVC
        elif kind == 'PersistentVolumeClaim':
            print(f"✅ process: {file_path}")
            try:
                if storage:
                    if 'spec' not in doc: doc['spec'] = {}
                    if 'resources' not in doc['spec']: doc['spec']['resources'] = {}
                    if 'requests' not in doc['spec']['resources']: doc['spec']['resources']['requests'] = {}
                    
                    current_storage = doc['spec']['resources']['requests'].get('storage')
                    if current_storage != storage:
                        doc['spec']['resources']['requests']['storage'] = storage
                        modified = True
                        print(f"   -> Updated PVC storage to {storage}")
            except KeyError:
                pass

    if modified:
        with open(file_path, 'w') as f:
            yaml.dump_all(documents, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Updated: {file_path}")

def main():
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file '{CSV_FILE}' not found.")
        return

    print(f"Starting Update. Scanning directories: {APP_SOURCE_DIRS}")
    
    with open(CSV_FILE, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            service_name = row.get('Service Name', '').strip()
            raw_cpu = row.get('CPU', '').strip()
            raw_ram = row.get('RAM', '').strip()
            raw_storage = row.get('storage', '').strip()
            
            if not service_name: continue
                
            cpu_val = format_cpu(raw_cpu)
            ram_val = format_mem(raw_ram)
            storage_val = format_storage(raw_storage)
            
            if not any([cpu_val, ram_val, storage_val]):
                continue

            print(f"Processing {service_name} (CPU:{cpu_val}, RAM:{ram_val}, HDD:{storage_val})...")
            
            # --- Logic ใหม่: วนหา Service ในทุก Folder ที่กำหนด ---
            found_service_dir = None
            
            for source_dir in APP_SOURCE_DIRS:
                potential_path = os.path.join(source_dir, service_name)
                if os.path.exists(potential_path):
                    found_service_dir = potential_path
                    break # เจอแล้วหยุดหาทันที (First match wins)
            
            if not found_service_dir:
                print(f"❌ Directory not found for service '{service_name}' in any configured paths.")
                continue
            
            # เมื่อเจอโฟลเดอร์แล้ว ก็เข้าไปหาไฟล์ YAML ข้างใน
            found_any_yaml = False
            for fname in os.listdir(found_service_dir):
                if fname.endswith('.yaml') or fname.endswith('.yml'):
                    fpath = os.path.join(found_service_dir, fname)
                    update_yaml_file(fpath, cpu_val, ram_val, storage_val, service_name)
                    found_any_yaml = True
            
            if not found_any_yaml:
                print(f"❌ No YAML files found in {found_service_dir}")

if __name__ == "__main__":
    main()