###
# To use this script, the [Invoke-build](https://github.com/nightroman/Invoke-Build)
# module must be installed:
#   Install-Module InvokeBuild
# To run tasks:
#   Invoke-build ?
###
# Build script parameters
param(
	[String]$Team = 'vw-cred-datalake',
	[String]$Name = "vw-cred-datalake",
	[String]$RepoLocation = "vwcredit/bica",
	[String]$RepoOwner = "vwcredit",
	[String]$Repo = "bica",
	[String]$Job = '',
	[String]$OldName = '',
	[Bool]$Unpause = $True
)

# Ensure IB works in the strict mode.
Set-StrictMode -Version Latest

# Synopsis: Test and Deploy.
task All Test, Deploy

# Synopsis: Removes the pipeline
task Destroy {
	fly -t $script:Team destroy-pipeline -p $script:Name
}

# Synopsis: Creates/updates and unpauses the pipeline
task Deploy{
	fly -t $script:Team set-pipeline -p $script:Name -c pipeline.yml -v TEAM_NAME=$script:Team -v REPO_LOCATION=$script:RepoLocation -v REPO=$script:Repo -v REPO_OWNER=$script:RepoOwner
	if ($script:Unpause) {
		fly -t $script:Team unpause-pipeline -p $script:Name
	}
}

task Rename{
	if ([string]::IsNullOrWhiteSpace($OldName)) {
		$OldName = Read-Host "Provide Old Pipeline Name:"
	}
	fly -t $script:Team rename-pipeline --old-name $script:OldName --new-name $script:Name
}

# Synopsis: Login to concourse
task Login {
	fly login --target $script:Team --team-name $script:Team --concourse-url https://ci.platform.vwfs.io
}

# Synopsis: Validate pipeline
task Test{
	fly validate-pipeline -c pipeline.yml
}

# Synopsis: Hijack job container 'Invoke-build hijack -Job job-name'
task Hijack {
	if ([string]::IsNullOrWhiteSpace($Job)) {
		$Job = Read-Host "Provide Job Name:"
	}
	fly -t $script:Team  hijack --job "$($script:Name)/$($Job)"
}

task Trigger {
	if ([string]::IsNullOrWhiteSpace($Job)) {
		$Job = Read-Host "Provide Job Name:"
	}
	fly -t $script:Team trigger-job --job "$($script:Name)/$($Job)"
}

task Watch {
	if ([string]::IsNullOrWhiteSpace($Job)) {
		$Job = Read-Host "Provide Job Name:"
	}
	fly -t $script:Team watch --job "$($script:Name)/$($Job)"
}

task TriggerAndWatch Trigger,Watch
task TestAndDeploy Test,Deploy