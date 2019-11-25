'''Watches AWS metadata API for spot termination notices on spot nodes.
Uses kubectl to drain nodes once their termination notice is present.'''

from os import getenv
from time import sleep
from subprocess import call, check_output, CalledProcessError
from requests import get


def print_pod_details(node_name):
    try:
        pod_details_command = ['kubectl', 'get', 'pods', '--all-namespaces',
                               '--field-selector=spec.nodeName={}'.format(node_name),
                               '-o', 'jsonpath={""}'
                                     '{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{" "}{end}']
        namespaces_command = ['kubectl', 'get', 'pods', '--all-namespaces',
                              '--field-selector=spec.nodeName={}'.format(node_name),
                              '-o', 'jsonpath={""}'
                                    '{range .items[*]}{.metadata.namespace}{" "}{end}']
        pod_details_list = check_output(pod_details_command).decode('utf-8').strip().split(' ')
        pod_details_list.sort()
        namespaces_list = list(set((check_output(namespaces_command).decode('utf-8')).strip().split(' ')))
        namespaces_list.sort()
        if pod_details_list != ['']:
            print('The following pods on the node {} will be evicted: {}'
                  .format(node_name, pod_details_list))
            print('Draining node {}, affected namespaces: {}'.format(node_name, namespaces_list))
        else:
            print('No pods found on the node {}'.format(node_name))
    except CalledProcessError as e:
        print('ERROR: Unable to fetch pod details: {}'.format(e))


def main():
    '''Watch for termination notices on spot instance nodes on AWS'''
    print('Starting up')

    node_name = getenv('NODE_NAME')

    print('Watching for termination notice on node %s' % node_name)

    counter = 0

    while True:
        response = get(
            "http://169.254.169.254/latest/meta-data/spot/termination-time"
        )
        if response.status_code == 200:
            kube_command = ['kubectl', 'drain', node_name,
                            '--grace-period=120', '--force',
                            '--ignore-daemonsets']

            print("Draining node: %s" % node_name)
            print_pod_details(node_name)
            result = call(kube_command)
            if result == 0:
                print('Node Drain successful')
                break

        else:
            if counter == 60:
                counter = 0
                print("Termination notice status: %s, on Node: %s" %
                      (response.status_code, node_name)
                      )
            counter += 5
            sleep(5)


if __name__ == '__main__':
    main()
