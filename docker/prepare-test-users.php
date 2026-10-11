<?php
// Build an import file using the existing role definitions exported by OJS.
// Run inside the container; no direct writes to the OJS database.
$ns = 'http://pkp.sfu.ca';
$doc = new DOMDocument();
$doc->load('/tmp/vestnik-users-base.xml');
$users = $doc->getElementsByTagNameNS($ns, 'users')->item(0);
while ($users->firstChild) {
    $users->removeChild($users->firstChild);
}
$accounts = json_decode(file_get_contents('/tmp/vestnik-test-users.json'), true, 512, JSON_THROW_ON_ERROR);
$add = function ($parent, $name, $value, $attrs = []) use ($doc, $ns) {
    $node = $doc->createElementNS($ns, $name);
    $node->appendChild($doc->createTextNode($value));
    foreach ($attrs as $key => $val) {
        $node->setAttribute($key, $val);
    }
    $parent->appendChild($node);
    return $node;
};
foreach ($accounts as $account) {
    $user = $doc->createElementNS($ns, 'user');
    $users->appendChild($user);
    foreach (['ru', 'en'] as $locale) {
        $add($user, 'givenname', $account['givenName'], ['locale' => $locale]);
    }
    foreach (['ru', 'en'] as $locale) {
        $add($user, 'familyname', $account['familyName'], ['locale' => $locale]);
    }
    $add($user, 'country', 'RU');
    $add($user, 'email', $account['email']);
    $add($user, 'username', $account['username']);
    $password = $doc->createElementNS($ns, 'password');
    $password->setAttribute('is_disabled', 'false');
    $password->setAttribute('must_change', 'false');
    $password->setAttribute('encryption', 'bcrypt');
    $user->appendChild($password);
    $add($password, 'value', password_hash($account['password'], PASSWORD_BCRYPT));
    $add($user, 'date_registered', '2026-10-07 00:00:00');
    $add($user, 'date_validated', '2026-10-07 00:00:00');
    $add($user, 'locales', 'ru:en');
    $membership = $doc->createElementNS($ns, 'user_user_group');
    $user->appendChild($membership);
    $add($membership, 'user_group_ref', $account['role']);
    $add($membership, 'date_start', '2026-10-07 00:00:00');
    $add($membership, 'masthead', 'false');
    if ($account['role'] === 'Reviewer') {
        $add($user, 'review_interests', 'информационные технологии:алгоритмы');
    }
}
if (!$doc->schemaValidate('/var/www/html/lib/pkp/plugins/importexport/users/pkp-users.xsd')) {
    throw new RuntimeException('Test user import XML is invalid');
}
$doc->save('/tmp/vestnik-test-users.xml');
echo "Prepared " . count($accounts) . " test users for the built-in importer.\n";
