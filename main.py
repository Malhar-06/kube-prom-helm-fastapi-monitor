from fastapi import FastAPI
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect

app = FastAPI()

@app.post("/createDeployment/{deployment_name}")
def create_deployment(deployment_name: str):
    """
    Create a Kubernetes deployment with the specified name.

    Args:
        deployment_name (str): The name of the deployment to create.

    Returns:
        dict: A dictionary containing a success message or an error message.
    """
    # Load the kubeconfig from the default location
    config.load_kube_config(config_file="/root/kube/config")
    v1 = client.AppsV1Api()

    # Define the deployment spec
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector={"matchLabels": {"app": deployment_name}},
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
                spec=client.V1PodSpec(containers=[client.V1Container(
                    name=deployment_name,
                    image="vimal13/apache-webserver-php",  # Example image, replace with your app image
                    ports=[client.V1ContainerPort(container_port=80)]
                    )]),
            )
        )
    )

    # Create the deployment
    try:
        v1.create_namespaced_deployment(namespace="default", body=deployment)
        return {"message": f"Deployment {deployment_name} created successfully"}
    except client.exceptions.ApiException as e:
        return {"error": e.reason}


@app.get("/getPromdetails")
def get_prom_details():
    prometheus_url = "http://prometheus-kube-prometheus-prometheus.prometheus.svc.cluster.local:9090/"
    prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)
    try:
        pod_metrics = prom.get_current_metric_value(metric_name='kube_pod_info')
        pod_details = []

        for metric in pod_metrics:
            pod_name = metric["metric"]["pod"]
            namespace = metric["metric"]["namespace"]
            node = metric["metric"]["node"]

            # CPU Usage
            cpu_query = f'rate(container_cpu_usage_seconds_total{{pod="{pod_name}", namespace="{namespace}"}}[5m])'
            cpu_usage = prom.custom_query(query=cpu_query)

            # Memory Usage
            memory_query = f'container_memory_usage_bytes{{pod="{pod_name}", namespace="{namespace}"}}'
            memory_usage = prom.custom_query(query=memory_query)


            pod_details.append({
                "pod_name": pod_name,
                "namespace": namespace,
                "node": node,
                "cpu_usage": cpu_usage[0]['value'][1] if cpu_usage else "0",
                "memory_usage": memory_usage[0]['value'][1] if memory_usage else "0",
            })

        return {"pod_details": pod_details}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)