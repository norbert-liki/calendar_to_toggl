import googleapiclient.discovery
import os


def create_instance(compute, project, zone, name):
    # Get the latest Debian image.
    image_response = compute.images().getFromFamily(
        project='debian-cloud', family='debian-10').execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/n1-standard-1" % zone
    startup_script = open(
        os.path.join(
            os.path.dirname(__file__), 'startup_train.sh'), 'r').read()

    config = {
        'name': name,
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Setting node to preemptible
        "scheduling": {
            "preemptible": True
        },

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/cloud-platform'
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script',
                'value': startup_script
            }]
        }
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()


def calendar_retrain(event=None, context=None, project="norbert-liki-sandbox", zone="us-central1-a", instance_name="calendar-retrain"):
    compute = googleapiclient.discovery.build('compute', 'v1')

    print('Creating instance.')
    create_instance(compute, project, zone, instance_name)

    print("Instance created")


if __name__ == "__main__":
    calendar_retrain()
