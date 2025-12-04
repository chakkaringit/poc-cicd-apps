import csv
import os
import yaml

# ================= CONFIGURATION =================
CSV_FILE = 'resources.csv'          # CSV file name
APPS_DIR = '../apps'                # Path to apps directory
# =================================================

def format_cpu(val):
    # If CSV contains just a number (e.g., 100), append 'm'
    val = str(val).strip()
    if not val: return None
    if val.isdigit(): return f"{val}m"
    return val

def format_mem(val):
    # If CSV contains just a number (e.g., 512), append 'Mi'
    val = str(val).strip()
    if not val: return None
    if val.isdigit(): return f"{val}Mi"
    return val

def format_storage(val):
    # If CSV contains just a number (e.g., 5), append 'Gi'
    val = str(val).strip()
    if not val: return None
    if val.isdigit(): return f"{val}Gi"
    return val

def update_yaml_file(file_path, cpu, ram, storage, service_name):
    try:
        with open(file_path, 'r') as f:
            # Load YAML as a list (to handle multi-document files)
            documents = list(yaml.safe_load_all(f))
    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")
        return
    
    modified = False
    
    for doc in documents:
        if not doc: continue
        kind = doc.get('kind')

        # ---------------------------------------------------------
        # CASE 1: Deployment / StatefulSet / DaemonSet (Update CPU/RAM)
        # ---------------------------------------------------------
        if kind in ['Deployment', 'StatefulSet', 'DaemonSet']:
            try:
                # 1. Update Container Resources
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
                
                # 2. Update StatefulSet Volume Templates (if present) - for Storage
                if kind == 'StatefulSet' and storage and 'volumeClaimTemplates' in doc['spec']:
                    for vct in doc['spec']['volumeClaimTemplates']:
                        if 'resources' not in vct['spec']: vct['spec']['resources'] = {}
                        if 'requests' not in vct['spec']['resources']: vct['spec']['resources']['requests'] = {}
                        
                        vct['spec']['resources']['requests']['storage'] = storage
                        modified = True
                        print(f"   -> Updated StatefulSet storage to {storage}")

            except KeyError:
                pass

        # ---------------------------------------------------------
        # CASE 2: Standalone PersistentVolumeClaim (Update Storage)
        # ---------------------------------------------------------
        elif kind == 'PersistentVolumeClaim':
            try:
                if storage:
                    if 'spec' not in doc: doc['spec'] = {}
                    if 'resources' not in doc['spec']: doc['spec']['resources'] = {}
                    if 'requests' not in doc['spec']['resources']: doc['spec']['resources']['requests'] = {}
                    
                    # Check current value first (skip if equal)
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
    # Check if CSV file exists
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file '{CSV_FILE}' not found.")
        return

    print("Starting Resource & Storage Update...")
    
    with open(CSV_FILE, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            # Match these keys with your CSV headers
            service_name = row.get('Service Name', '').strip()
            raw_cpu = row.get('CPU', '').strip()
            raw_ram = row.get('RAM', '').strip()
            raw_storage = row.get('Storage', '').strip()
            
            if not service_name: continue
                
            cpu_val = format_cpu(raw_cpu)
            ram_val = format_mem(raw_ram)
            storage_val = format_storage(raw_storage)
            
            # Skip if there are no values to update
            if not any([cpu_val, ram_val, storage_val]):
                continue

            print(f"Processing {service_name} (CPU:{cpu_val}, RAM:{ram_val}, HDD:{storage_val})...")
            
            target_dir = os.path.join(APPS_DIR, service_name)
            
            if not os.path.exists(target_dir):
                print(f"❌ Directory not found: {target_dir}")
                continue
                
            # Scan for all YAML files in that directory
            # We read every file to check if it contains PVC or Workload definitions
            found_any = False
            for fname in os.listdir(target_dir):
                if fname.endswith('.yaml') or fname.endswith('.yml'):
                    fpath = os.path.join(target_dir, fname)
                    update_yaml_file(fpath, cpu_val, ram_val, storage_val, service_name)
                    found_any = True
            
            if not found_any:
                print(f"❌ No YAML files found in {service_name}")

if __name__ == "__main__":
    main()