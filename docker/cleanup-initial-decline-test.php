<?php
require '/var/www/html/tools/bootstrap.php';
class DeskTestCleanup extends \PKP\cliTool\CommandLineTool {
 public function execute(){ $s=\APP\facades\Repo::submission()->get(6); if(!$s||$s->getData('contextId')!==1||$s->getData('status')!==4)throw new \Exception('not the declined test submission'); $p=\APP\facades\Repo::publication()->get($s->getData('currentPublicationId')); if($p->getData('title','en')!=='Temporary test of desk rejection')throw new \Exception('unexpected title'); \APP\facades\Repo::submission()->delete($s);echo "Removed temporary desk-rejection test 6 through native repository\n"; }
}
(new DeskTestCleanup($argv))->execute();
