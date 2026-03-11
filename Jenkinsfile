pipeline {
    agent any

    parameters {
        string(name: 'INPUT_CLUSTER_NAME', defaultValue: 'My-Jenkins-Cluster', description: 'Target EKS Cluster Name')
        string(name: 'GIT_REPO_URL', defaultValue: 'https://github.com/chakkaringit/poc-cicd-apps.git', description: 'GitOps Repository URL')
        choice(name: 'SUBSCRIPTION_TIER', choices: ['starter', 'basic', 'power'], description: 'Service Level Agreement')
        string(name: 'WILDCARD_DOMAIN', defaultValue: 'prod.knowesis.quiinsfelicity.shop', description: 'Wildcard Domain Name with environment and company name (e.g. prod.knowesis.quiinsfelicity.shop)')
        string(name: 'INPUT_AWS_REGION', defaultValue: 'ap-southeast-1', description:'Infra Region ap-southeast-1)')
    }

    environment {
        //AWS_REGION = 'ap-southeast-1'
        AWS_REGION = "${params.INPUT_AWS_REGION}"
        
        // ID ของ Credential ใน Jenkins
        AWS_CRED_ID = 'maas-aws-key-main'
        GIT_CRED_ID = 'github-login' // Credential GitHub (Username/Token)
        
        // Path ของไฟล์ใน Git Repo
        SECRET_TEMPLATE_PATH = 'cluster-config/argocd/repo-secret.yaml'
        ROOT_DB_PATH = 'cluster-config/root-app-db.yaml'
        ROOT_APP_PATH = 'cluster-config/root-app.yaml'
    }

    stages {
        stage('Checkout Code') {
            steps {
                script { cleanWs() }
                // ดึง Code มาเพื่อเอาไฟล์ YAML Template
                git branch: 'main', 
                    credentialsId: GIT_CRED_ID,
                    url: params.GIT_REPO_URL
            }
        }

        stage('Configure ArgoCD') {
            steps {
                script {
                    echo "Configuring ArgoCD on Cluster: ${params.INPUT_CLUSTER_NAME}..."
                    def customKubeConfig = "${WORKSPACE}/.kubeconfig-temp"
                    env.TIER_OVERLAY = params.SUBSCRIPTION_TIER.toLowerCase()
                    env.WILDCARD_DOMAIN = params.WILDCARD_DOMAIN.toLowerCase()
                    
                    withCredentials([
                        [$class: 'AmazonWebServicesCredentialsBinding', credentialsId: AWS_CRED_ID, accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
                        // ดึง User/Token ของ Git มาใส่ตัวแปร Environment
                        usernamePassword(credentialsId: GIT_CRED_ID, usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')
                    ]) {
                        
                        // 1. Login EKS
                        sh "aws eks update-kubeconfig --name ${params.INPUT_CLUSTER_NAME} --region ${AWS_REGION} --kubeconfig ${customKubeConfig}"
                        
                        withEnv(["KUBECONFIG=${customKubeConfig}"]) {
                            
                            // 2. ตรวจสอบว่ามี Namespace argocd หรือยัง (กันเหนียว)
                            sh "kubectl create namespace opolo --dry-run=client -o yaml | kubectl apply -f -"
                            sh "kubectl -n opolo create secret docker-registry regcred --docker-username=kw-rm@knowesis.com --docker-password=Kwrelease@321 --dry-run=client -o yaml | kubectl apply -f -"
                            // 3. Inject Secret (สร้างการเชื่อมต่อกับ Private Repo)
                            echo "Creating Git Repository Secret..."
                            // ใช้ envsubst แทนค่า ${GIT_USER} และ ${GIT_TOKEN} ลงในไฟล์ YAML
                            //sh "envsubst < ${SECRET_TEMPLATE_PATH} | kubectl apply -f -"
                            
                            // 4. Apply Root App (App of Apps)
                            echo "Deploying Root Application..."
                            //sh "kubectl apply -f ${ROOT_APP_PATH}"
                            sh "envsubst < ${ROOT_DB_PATH} | kubectl apply -f -"
                            
                            echo "✅ Configuration Applied with Tier: ${env.TIER_OVERLAY}"
                            
                            echo "⏳ Waiting for Persistence Layer..."
                            sleep 300
                            
                            // ท่ายาก: วนลูปเช็คสถานะ
                            timeout(time: 5, unit: 'MINUTES') {
                                sh """
                                  until kubectl get application sift-persist -n argocd -o jsonpath='{.status.health.status}' | grep -q Healthy; do
                                    echo "Waiting for sift-persist to be Healthy..."
                                    sleep 30
                                  done
                                """
                            }
            
                            echo "✅ Configuration Applied Successfully!"
                        }
                    }
                }
            }
        }

        stage('Deploy Wave 2: Apps') {
            steps {
                script {
                    echo "Configuring ArgoCD on Cluster: ${params.INPUT_CLUSTER_NAME}..."
                    def customKubeConfig = "${WORKSPACE}/.kubeconfig-temp"
                    env.TIER_OVERLAY = params.SUBSCRIPTION_TIER.toLowerCase()
                    env.WILDCARD_DOMAIN = params.WILDCARD_DOMAIN.toLowerCase()
                    
                    withCredentials([
                        [$class: 'AmazonWebServicesCredentialsBinding', credentialsId: AWS_CRED_ID, accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
                        // ดึง User/Token ของ Git มาใส่ตัวแปร Environment
                        usernamePassword(credentialsId: GIT_CRED_ID, usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')
                    ]) {
                        
                        // 1. Login EKS
                        sh "aws eks update-kubeconfig --name ${params.INPUT_CLUSTER_NAME} --region ${AWS_REGION} --kubeconfig ${customKubeConfig}"
                        
                        withEnv(["KUBECONFIG=${customKubeConfig}"]) {
                            
                            // 2. ตรวจสอบว่ามี Namespace argocd หรือยัง (กันเหนียว)
                            sh "kubectl create namespace opolo --dry-run=client -o yaml | kubectl apply -f -"
                            //sh "kubectl -n opolo create secret docker-registry regcred --docker-username=kw-rm@knowesis.com --docker-password=Kwrelease@321 --dry-run=client -o yaml | kubectl apply -f -"
                            // 3. Inject Secret (สร้างการเชื่อมต่อกับ Private Repo)
                            echo "Creating Git Repository Secret..."
                            // ใช้ envsubst แทนค่า ${GIT_USER} และ ${GIT_TOKEN} ลงในไฟล์ YAML
                            //sh "envsubst < ${SECRET_TEMPLATE_PATH} | kubectl apply -f -"
                            
                            // 4. Apply Root App (App of Apps)
                            echo "Deploying Application..."
                            //sh "kubectl apply -f ${ROOT_APP_PATH}"
                            sh "envsubst < ${ROOT_APP_PATH} | kubectl apply -f -"
                            
                            echo "✅ Configuration Applied with Tier: ${env.TIER_OVERLAY}"
                            
                            echo "⏳ Waiting for Apps Layer..."
                            sleep 300
                            
                            // ท่ายาก: วนลูปเช็คสถานะ
                            timeout(time: 5, unit: 'MINUTES') {
                                sh """
                                  until kubectl get application persistance-api -n argocd -o jsonpath='{.status.health.status}' | grep -q Healthy; do
                                    echo "Waiting for persistance-api to be Healthy..."
                                    sleep 30
                                  done
                                """
                            }
            
                            echo "✅ Configuration Applied Successfully!"
                        }
                    }
                }
            }
        }
        
        stage('Verify Sync Status') {
            steps {
                script {
                    echo "Checking ArgoCD Applications..."
                    def customKubeConfig = "${WORKSPACE}/.kubeconfig-temp"
                    
                    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: AWS_CRED_ID, accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']]) {
                         withEnv(["KUBECONFIG=${customKubeConfig}"]) {
                             // รอสักพักให้ ApplicationSet ทำงาน
                             sleep 10
                             
                             echo "List of Applications created by ArgoCD:"
                             try {
                                 // แสดงรายการ App ทั้งหมดที่ถูกสร้างขึ้นมา
                                 sh "kubectl get applications -n argocd"
                             } catch (Exception e) {
                                 echo "No applications found yet. Check ArgoCD logs if needed."
                             }
                         }
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo "🚀 GitOps Pipeline Finished! ArgoCD is now syncing all your services."
        }
        failure {
            echo "❌ Pipeline Failed."
        }
    }
}