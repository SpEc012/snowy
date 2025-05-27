<?php
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

$keyauth_base_url = 'https://keyauth.win/api/1.2/';

// Get request data
$request_type = $_GET['request_type'] ?? '';
$data = json_decode(file_get_contents('php://input'), true) ?? [];

// KeyAuth credentials
$app_name = "Raven";
$owner_id = "HgQcPwtKnr";
$secret = "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623";

function make_keyauth_request($endpoint, $params) {
    global $keyauth_base_url;
    
    $url = $keyauth_base_url . '?' . http_build_query($params);
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    curl_close($ch);
    
    if ($http_code !== 200) {
        return json_encode(['success' => false, 'message' => 'Request failed']);
    }
    
    return $response;
}

switch ($request_type) {
    case 'init':
        $params = [
            'type' => 'init',
            'name' => $app_name,
            'ownerid' => $owner_id,
            'ver' => $data['version'] ?? '1.0'
        ];
        echo make_keyauth_request('', $params);
        break;
        
    case 'login':
        $params = [
            'type' => 'login',
            'username' => $data['username'] ?? '',
            'pass' => $data['password'] ?? '',
            'sessionid' => $data['sessionid'] ?? '',
            'name' => $app_name,
            'ownerid' => $owner_id
        ];
        echo make_keyauth_request('', $params);
        break;
        
    case 'register':
        $params = [
            'type' => 'register',
            'username' => $data['username'] ?? '',
            'pass' => $data['password'] ?? '',
            'key' => $data['key'] ?? '',
            'email' => $data['email'] ?? '',
            'sessionid' => $data['sessionid'] ?? '',
            'name' => $app_name,
            'ownerid' => $owner_id
        ];
        echo make_keyauth_request('', $params);
        break;
        
    case 'logout':
        $params = [
            'type' => 'logout',
            'sessionid' => $data['sessionid'] ?? '',
            'name' => $app_name,
            'ownerid' => $owner_id
        ];
        echo make_keyauth_request('', $params);
        break;
        
    default:
        echo json_encode(['success' => false, 'message' => 'Invalid request type']);
}
