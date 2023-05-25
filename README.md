# lambda-finops-email-totals

An AWS Lambda for emailing monthly totals to tagged resource owners

## Design

This lambda will query Cost Explorer for our Owner Email cost category, query
Synapse for the members of Team Sage, and email a monthly total to internal Sage
users who have been tagged as resource owners.

### Parameters

| Parameter Name      | Allowed Values                                                                                                             | Default Value         | Description                                                                          |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------ |
| ScheduleExpression  | [EventBridge Schedule Expression](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents-expressions.html) | `cron(30 10 2 * ? *)` | Schedule for running the lambda                                                      |
| SenderEmail         | any email address                                                                                                          | `it@sagebase.org`     | Value to use for the `From` email field                                              |
| RestrictRecpipients | `True` or `False`                                                                                                          | `True`                | Only send emails to recipients listed in `ApprovedRecipients`                        |
| ApprovedRecpipients | Comma-delimited list of email addresses                                                                                    | `None`                | If `RestrictRecpipients` is `True`, then only send emails to recipients in this list |
| MinimumValue        | Floating-point number                                                                                                      | `1.0`                 | Emails will not be sent for totals less than this amount                             |

### Triggering

The lambda is configured to run on a schedule, by default at 10:30am UTC on the 2nd of each month.

## Development

### Contributions

Contributions are welcome.

### Setup Development Environment

Install the following applications:

- [AWS CLI](https://github.com/aws/aws-cli)
- [AWS SAM CLI](https://github.com/aws/aws-sam-cli)
- [pre-commit](https://github.com/pre-commit/pre-commit)
- [pipenv](https://github.com/pypa/pipenv)

Check in [.travis.yml](./.travis.yml) to see how they are installed for this
repo.

### Install Requirements

Run `pipenv install --dev` to install both production and development
requirements, and `pipenv shell` to activate the virtual environment. For more
information see the [pipenv docs](https://pipenv.pypa.io/en/latest/).

After activating the virtual environment, run `pre-commit install` to install
the [pre-commit](https://pre-commit.com/) git hook.

### Update Requirements

First, make any needed updates to the base requirements in `Pipfile`, then use
`pipenv` to regenerate both `Pipfile.lock` and `requirements.txt`. We use
`pipenv` to control versions in testing, but `sam` relies on `requirements.txt`
directly for building the container used by the lambda.

```shell script
$ pipenv update
$ pipenv requirements > requirements.txt
```

Additionally, `pre-commit` manages its own requirements.

```shell script
$ pre-commit autoupdate
```

### Create a local build

```shell script
$ sam build
```

### Run unit tests

Tests are defined in the `tests` folder in this project. Use PIP to install the
[pytest](https://docs.pytest.org/en/latest/) and run unit tests.

```shell script
$ python -m pytest tests/ -v
```

### Run integration tests

Running integration tests
[requires docker](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-local-start-api.html)

```shell script
$ sam local invoke HelloWorldFunction --event events/event.json
```

## Deployment

### Deploy Lambda to S3

Deployments are sent to the
[Sage cloudformation repository](https://bootstrap-awss3cloudformationbucket-19qromfd235z9.s3.amazonaws.com/index.html)
which requires permissions to upload to Sage
`bootstrap-awss3cloudformationbucket-19qromfd235z9` and
`essentials-awss3lambdaartifactsbucket-x29ftznj6pqw` buckets.

```shell script
sam package --template-file .aws-sam/build/template.yaml \
  --s3-bucket essentials-awss3lambdaartifactsbucket-x29ftznj6pqw \
  --output-template-file .aws-sam/build/lambda-template.yaml

aws s3 cp .aws-sam/build/lambda-template.yaml s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/lambda-template/master/
```

## Publish Lambda

### Private access

Publishing the lambda makes it available in your AWS account. It will be
accessible in the
[serverless application repository](https://console.aws.amazon.com/serverlessrepo).

```shell script
sam publish --template .aws-sam/build/lambda-template.yaml
```

### Public access

Making the lambda publicly accessible makes it available in the
[global AWS serverless application repository](https://serverlessrepo.aws.amazon.com/applications)

```shell script
aws serverlessrepo put-application-policy \
  --application-id <lambda ARN> \
  --statements Principals=*,Actions=Deploy
```

## Install Lambda into AWS

### Sceptre

Create the following [sceptre](https://github.com/Sceptre/sceptre) file
config/prod/lambda-template.yaml

```yaml
template:
  type: http
  url: "https://PUBLISH_BUCKET.s3.amazonaws.com/lambda-template/VERSION/lambda-template.yaml"
stack_name: "lambda-template"
stack_tags:
  Department: "Platform"
  Project: "Infrastructure"
  OwnerEmail: "it@sagebase.org"
```

Install the lambda using sceptre:

```shell script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/lambda-template.yaml
```

### AWS Console

Steps to deploy from AWS console.

1. Login to AWS
1. Access the
   [serverless application repository](https://console.aws.amazon.com/serverlessrepo)
   -> Available Applications
1. Select application to install
1. Enter Application settings
1. Click Deploy

## Releasing

We have setup our CI to automate a releases. To kick off the process just create
a tag (i.e 0.0.1) and push to the repo. The tag must be the same number as the
current version in [template.yaml](template.yaml). Our CI will do the work of
deploying and publishing the lambda.
