#!/usr/bin/env bash
# Runs on the GitHub Actions runner: sends a shell script to the EC2 host through AWS Systems
# Manager (Run Command) and waits for the result. No SSH, no open port 22.
#
#   bash scripts/ssm-run.sh "comment" <<'EOF'
#   ...script executed as root on the server...
#   EOF
#
# Needs EC2_INSTANCE_ID in the environment and AWS credentials already configured.
set -euo pipefail

: "${EC2_INSTANCE_ID:?Set the EC2_INSTANCE_ID repository variable}"
comment="${1:-deploy}"
script=$(cat)

# The whole script travels as one command; SSM writes it to a file and runs it as root.
parameters=$(jq -n --arg script "$script" '{commands: [$script], executionTimeout: ["1200"]}')

command_id=$(
  aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name AWS-RunShellScript \
    --comment "${comment:0:100}" \
    --parameters "$parameters" \
    --query Command.CommandId \
    --output text
)
echo "SSM command $command_id sent to $EC2_INSTANCE_ID"

status=Pending

# Up to 20 minutes. Right after sending, the invocation may not exist yet, hence "|| echo Pending".
for _ in $(seq 1 240); do
  sleep 5
  status=$(
    aws ssm get-command-invocation \
      --command-id "$command_id" \
      --instance-id "$EC2_INSTANCE_ID" \
      --query Status \
      --output text 2>/dev/null || echo Pending
  )
  case "$status" in
    Pending | InProgress | Delayed) ;;
    *) break ;;
  esac
done

invocation() {
  aws ssm get-command-invocation \
    --command-id "$command_id" \
    --instance-id "$EC2_INSTANCE_ID" \
    --query "$1" \
    --output text
}

echo "== Server output"
invocation StandardOutputContent
invocation StandardErrorContent >&2

if [ "$status" != "Success" ]; then
  echo "The SSM command finished with status $status." >&2
  exit 1
fi
