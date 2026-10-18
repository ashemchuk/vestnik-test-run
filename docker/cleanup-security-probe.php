<?php
require '/var/www/html/tools/bootstrap.php';
class ProbeCleanup extends \PKP\cliTool\CommandLineTool {
 public function execute(){ $s=\APP\facades\Repo::submission()->get(5); if(!$s||$s->getData('contextId')!==1||$s->getData('submissionProgress')!=='start')throw new \Exception('not the disposable draft'); \APP\facades\Repo::submission()->delete($s);echo "Removed disposable security draft 5 through native repository\n"; }
}
(new ProbeCleanup($argv))->execute();
