# lambda-finops-email-totals

An AWS Lambda for emailing monthly totals to tagged resource owners

## Design

This lambda will query Cost Explorer for our Owner Email cost category, query
Synapse for the members of Team Sage, and email a monthly total to internal Sage
users who have been tagged as resource owners.

### Parameters

| Parameter Name     | Allowed Values                          | Default Value                           | Description                                                                          |
| ------------------ | --------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------ |
| ScheduleExpression | EventBridge Schedule Expression         | `cron(30 10 2 * ? *)`                   | Schedule for running the lambda                                                      |
| AdminEmail         | Any email address                       | `cloud-cost-notifications@sagebase.org` | Send a report on unowned costs to this address                                       |
| SenderEmail        | Any email address                       | `cloud-cost-notifications@sagebase.org` | Value to use for the `From` email field                                              |
| SkipRecipients     | Comma-delimited list of email addresses | `''`                                    | Never send emails to recipients in this list (recipient opt-out)                     |
| MinimumValue       | Floating-point number                   | `1.0`                                   | Emails will not be sent for totals less than this amount                             |
| SynapseDomain      | Valid domain, prepended with `@`        | `@synapse.org`                          | Email domain used by Synapse                                                         |
| SynapseTeamId      | Synapse Team Id (numeric string)        | `273957`                                | Only send emails to synapse users if they are a member of this Team                  |
| RestrictRecipients | `True` or `False`                       | `False`                                 | If `True` only send emails to recipients listed in `ApprovedRecipients`              |
| ApprovedRecipients | Comma-delimited list of email addresses | `''`                                    | If `RestrictRecpipients` is `True`, then only send emails to recipients in this list |
| CopyRecipients     | Comma-delimited list of email addresses | `''`                                    | CC this list of recipients on all emails                                             |

#### ScheduleExpression

[EventBridge schedule expression](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents-expressions.html)
describing how often to run the lambda. By default it runs at 10:30am UTC on the
2nd of each month.

#### AdminEmail

An administrative report summarizing unowned costs per account will be sent to
this address.

#### SenderEmail

This email address will appear is the `From` field, and must be
[verified](https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html)
before emails will successfully send.

#### SkipRecipients

A skip list of email addresses. Any recipient listed here will be skipped,
useful for recipients who want to opt-out of notifications.

#### MinimumValue

Don't send an email if the reported monthly total is less than this amount, by
default $1.

#### SynapseDomain

The email domain used by Synapse. If an email recipient is at this domain, the
recipient must also be a member of the listed Synapse team.

#### SynapseTeamId

Only send notifications to Synapse users if they are also a member of this team.
This only affects email addresses matching SynapseDomain.

#### RestrictRecipients

Boolean value to toggle enforcing an `ApprovedRecipients` allow list of email
recipients. Useful for testing.

#### ApprovedRecipients

An allow list of recipient addresses, any recipient not listed here will be
skipped, only respected when `RestrictRecipients` is `True`. Does not override
`SkipRecipients`. Useful for testing.

#### CopyRecipients

A list of email addresses to CC on all emails.

### Triggering

The lambda is configured to run on a schedule, by default at 10:30am UTC on the
2nd of each month. Ad-hoc runs for testing can be triggered with an empty test
event from the
[Lambda console page](https://docs.aws.amazon.com/lambda/latest/dg/testing-functions.html)

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
`pipenv` to regenerate both `Pipfile.lock` and `requirements.txt`.

```shell script
$ pipenv update --dev
```

We use `pipenv` to control versions in testing, but `sam` relies on
`requirements.txt` directly for building the lambda artifact, so we dynamically
generate `requirements.txt` from `Pipfile.lock` before building the artifact.
The file must be created in the `CodeUri` directory specified in
`template.yaml`.

```shell script
$ pipenv requirements > requirements.txt
```

Additionally, `pre-commit` manages its own requirements.

```shell script
$ pre-commit autoupdate
```

### Create a local build

Use a Lambda-like docker container to build the Lambda artifact

```shell script
$ sam build --use-container
```

### Run unit tests

Tests are defined in the `tests` folder in this project, and dependencies are
managed with `pipenv`. Install the development dependencies and run the tests
using `coverage`.

```shell script
$ pipenv run coverage run -m pytest tests/ -svv
```

Automated testing will upload coverage results to [Coveralls](coveralls.io).

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

When using AWS Organizations, the lambda should be deployed once in the master
account to aggregate all costs from the member accounts. Otherwise it must be
deployed into each separate account, resulting in a separate email for each
account total.

### Sceptre

Create the following [sceptre](https://github.com/Sceptre/sceptre) file
config/prod/lambda-template.yaml

```yaml
template:
  type: http
  url: "https://PUBLISH_BUCKET.s3.amazonaws.com/lambda-template/VERSION/lambda-template.yaml"
stack_name: "lambda-template"
stack_tags:
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

### Initial Deploy

Some manual verification and testing must be performed with the initial deploy.

#### Sender Email Verification

In order for SES to send emails, the sender address must be
[verified](https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html)
prior to the first run of the lambda.

#### Canary Email Verification

If the AWS Account is in the SES Sandbox, then recipient addresses will also
need to be
[verified](https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html)
prior to the first run of the lambda.

#### Canary Run

Once the needed addresses have been verified, the lambda should be tested with a
canary run, restricting output to a list of approved canary users by using the
`RestrictRecipients` and `ApprovedRecipients` parameters.

```yaml
template:
  type: http
  url: "https://PUBLISH_BUCKET.s3.amazonaws.com/lambda-template/VERSION/lambda-template.yaml"
stack_name: "lambda-template"
stack_tags:
  OwnerEmail: "it@sagebase.org"
parameters:
  RestrictRecipients: "True"
  ApprovedRecipients: "canary1@example.com,canary2@example.com"
```

#### Exit SES Sandbox

Once the sender email address has been verified and a canary run has succeeded,
the AWS account must be move out of the
[SES Sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html).

#### Full Deploy

After moving the AWS account out of the SES Sandbox, redeploy the lambda without
recipient restrictions and with any other needed parameters.

```yaml
template:
  type: http
  url: "https://PUBLISH_BUCKET.s3.amazonaws.com/lambda-template/VERSION/lambda-template.yaml"
stack_name: "lambda-template"
stack_tags:
  OwnerEmail: "it@sagebase.org"
parameters:
  RestrictRecipients: "False"
  CopyRecipients: "aws-costs@sagebase.org"
```
