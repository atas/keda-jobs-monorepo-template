apiVersion: v1
kind: Secret
metadata:
  name: r2-secret
  namespace: keda-jobs-prod
  labels:
    app.kubernetes.io/name: keda-jobs
type: Opaque
stringData:
  R2_ACCOUNT_ID: "${R2_ACCOUNT_ID}"
  R2_ACCESS_KEY_ID: "${R2_ACCESS_KEY_ID}"
  R2_SECRET_ACCESS_KEY: "${R2_SECRET_ACCESS_KEY}"
