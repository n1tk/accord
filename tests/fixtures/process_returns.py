
RUNNING_PODS = """
NAME                                                              READY
STATUS    RESTARTS   AGE\n
anaconda-enterprise-ap-auth-68c4f864f8-x8trs                      1/1
Running   0          30m\n
anaconda-enterprise-ap-auth-api-6cb6f9595d-9c774                  1/1
Running   0          30m\n
anaconda-enterprise-ap-auth-escrow-7f597cfd7-kf4gs                1/1
Running   0          30m\n
anaconda-enterprise-ap-deploy-58458665cf-lhc79                    1/1
Running   0          30m\n
anaconda-enterprise-ap-docs-6d6cff47-6j7ld                        1/1
Running   0          30m\n
anaconda-enterprise-ap-git-storage-56fcfc56b9-2ml4d               2/2
Running   0          30m\n
anaconda-enterprise-ap-object-storage-586f97d7cf-mlzww            1/1
Running   0          30m\n
anaconda-enterprise-ap-repository-86d44d6c84-5dtmj                1/1
Running   0          30m\n
anaconda-enterprise-ap-storage-84946bc54d-lfxvk                   1/1
Running   0          30m\n
anaconda-enterprise-ap-ui-798b4477cc-fk626                        1/1
Running   0          30m\n
anaconda-enterprise-ap-workspace-68cf65df9f-97vx7                 1/1
Running   0          30m\n
anaconda-enterprise-app-images-h8lkp                              3/3
Running   0          29m\n
anaconda-enterprise-nginx-ingress-rc-4vgbc                        1/1
Running   0          29m\n
anaconda-enterprise-postgres-58857557d-ctbfs                      1/1
Running   0          30m\n
""".encode('utf-8')


DEPLOYMENTS_POSTGRES = (
    '{"id": "72c1caccc2144afe925b4367f377a07f","name": '
    '"house_price_predictions", "owner": "anaconda-enterprise", "type": "app",'
    '"state_change_token": null, "state_change_started": null,'
    '"status_text": "Started", "url": "https://test.url.com/",'
    '"command_name": "default", "project_name": "house_price_predictions", '
    '"project_revision": "0.1.0","project_owner": "anaconda-enterprise"}'
).encode('utf-8')


CM_BACKUP_FILE = [
    'apiVersion: v1',
    'data:',
    '  hostname: test.domain.com',
    'kind: ConfigMap',
    'metadata:',
    '  annotations:',
    '    kubectl.kubernetes.io/last-applied-configuration: test',
    '  creationTimestamp: 2019-06-10T14:03:50Z',
    '  name: anaconda-enterprise-install',
    '  namespace: default',
    '  resourceVersion: "289"',
    '  selfLink: /api/v1/namespaces/default/configmaps/testing',
    '  uid: 9295027c-8b88-11e9-badd-067b7383aa6c'
]


SECRET_BACKUP_FILE = [
    'apiVersion: v1',
    'data:',
    '  testing: dGVzdGluZw==',
    'kind: Secret',
    'metadata:',
    '  creationTimestamp: 2019-06-10T19:38:28Z',
    '  labels:',
    '    anaconda-owner: user-creds-anaconda-enterprise',
    '  name: anaconda-credentials-user-creds-anaconda-enterprise-3ggji6dp',
    '  namespace: default',
    '  resourceVersion: "25913"',
    '  selfLink: /api/v1/namespaces/default/secrets/secret-testing',
    '  uid: 521f2ba5-8bb7-11e9-badd-067b7383aa6c',
    'type: Opaque'
]

CM_EXPECTED = [
    'apiVersion: v1\n',
    'data:\n',
    '  hostname: test.domain.com\n',
    'kind: ConfigMap\n',
    'metadata:\n',
    '  annotations:\n',
    '    kubectl.kubernetes.io/last-applied-configuration: test\n',
    '  name: anaconda-enterprise-install\n',
    '  namespace: default\n'
]


SECRECT_EXPECTED = [
    'apiVersion: v1\n',
    'data:\n',
    '  testing: dGVzdGluZw==\n',
    'kind: Secret\n',
    'metadata:\n',
    '  labels:\n',
    '    anaconda-owner: user-creds-anaconda-enterprise\n',
    '  name: anaconda-credentials-user-creds-anaconda-enterprise-3ggji6dp\n',
    '  namespace: default\n',
    'type: Opaque\n'
]
