---
title: API Reference

toc_footers:
  - <a href='#'>Sign Up for a Developer Key</a>
  - <a href='http://github.com/tripit/slate'>Documentation Powered by Slate</a>

includes:
  - errors

search: true

---

# Introduction

Welcome to the MetaDisk API! Storj allows users to buy and sell their extra hard drive space into a global network. Storj uses a variety of technology including P2P networks, encryption, cryptographic auditing, and the Bitcoin blockchain to keep this network secure, private, and robust. These technologies make Storj a solid, but complex platform.

MetaDisk will simplify that significantly by providing a simple API, service, and toolset to allow developers to PUT and GET data from the Storj platform. It also allows developers to pay via dollars, and not have to deal with the complexity of Bitcoin or other cryptocurrencies.

# MetaDisk Rules
1. MetaDisk is a zero knowledge system. No plaintext data, no keys, or file metadata should ever stored or held by the service.
2. MetaDisk is a transparent service, not a black box like traditional data storage services. File network status, node status, and independent audits of files should be able to be done at all times.


# File Upload
>To upload file, use this code:

```shell
    curl
        -F"data_hash=3b438fd7b1f223890f18f8ffc50c19c00b08340fc4fc76a94ba3a1c160b332a0" \
        -F"file_role=000" -F"file_data=@file_name" \
        -H"sender_address: mn45zPRtyy159spQ77gR43NoJmZiw2fN3a" \
        -H"signature: IMiZ0ZJhC5kdORnGnfwBJm7ikyDSrl0Icqepd6XZIJCynYd5GLITTCbk4vCxuvGgnj4Z24ay6niXmqFxkctqu8U" \
        /api/files/ 
```

>The above command returns JSON structured like this:

```json
{
  "data_hash": "3b438fd7b1f223890f18f8ffc50c19c00b08340fc4fc76a94ba3a1c160b332a0",
  "file_role": "000"
}
```


User can upload data via POST to an end node.

### HTTP Request

`POST /api/files/`

### Query Parameters

Type | Params | Values | Description
--------- | ------- | ----------- | ----------------
POST | data_hash | string | data_hash must be sent with each request. It ensures that the data passed to the endpoint has not been modified in transit. data_hash should be the SHA-256 hash of file_data
POST | file_role | string | The uploading party needs to be able to set file roles. For example, if anyone can retrieve this file or only specified addresses. It contains three digits.
POST | file_data | binary file | Encrypted shard of the data. To ensure properly handling under the current specifications file_data should not be larger than 128 MB.
HEADER | sender_address | string | The Bitcoin public key of the user that is trying to POST data.
HEADER | signature | string | Produced by signing `data_hash` by the private key belonging to `sender_address`.


# File Download

User can download data via GET from an end node.

Type | Params | Values | Description
--------- | ------- | ----------- | ----------------
HEADER | sender_address | string | The Bitcoin public key of the user that is trying to POST data.
HEADER | signature | string | Produced by signing `data_hash` by the private key belonging to `sender_address`.

>To download data, use this code:

```shell
curl
    -X GET -H "Content-type: application/json" \
    -H "Accept: application/json" \
        -H"sender_address: mn45zPRtyy159spQ77gR43NoJmZiw2fN3a" \
        -H"signature: IMiZ0ZJhC5kdORnGnfwBJm7ikyDSrl0Icqepd6XZIJCynYd5GLITTCbk4vCxuvGgnj4Z24ay6niXmqFxkctqu8U" \
    /api/files/3b438fd7b1f223890f18f8ffc50c19c00b08340fc4fc76a94ba3a1c160b332a0
```

> The above command returns binary file data.

### HTTP Request

`GET /api/files/<data_hash>`


# Node Info

A quick glance at the nodes data usage.

```shell
curl
    -X GET -H "Content-type: application/json" -H "Accept: application/json" \
    /api/nodes/me/
```

> The above command returns JSON structured like this:

```json
{
  "bandwidth": {
    "current": {
      "incoming": 42,
      "outgoing": 47
    },
    "limits": {
      "incoming": 1048576,
      "outgoing": 2097152
    },
    "total": {
      "incoming": 42,
      "outgoing": 47
    }
  },
  "storage": {
    "capacity": 104857600,
    "max_file_size": 14,
    "used": 42
  }
}
```

### HTTP Request

`GET /api/nodes/me`


# File List

Get all files currently listed on the node.

```shell
curl
    -X GET -H "Content-type: application/json" -H "Accept: application/json" \
    /api/files/
```

> The above command returns JSON structured like this:

```json
["3b438fd7b1f223890f18f8ffc50c19c00b08340fc4fc76a94ba3a1c160b332a0"]
```

### HTTP Request

`GET /api/files/`


# File Audit
>To audit file, use this code:

```shell
    curl
        -F"data_hash=3a6eb0790f39ac87c94f3856b2dd2c5d110e6811602261a9a923d3bb23adc8b7" \
        -F"challenge_seed=19b25856e1c150ca834cffc8b59b23adbd0ec0389e58eb22b3b64768098d002b"\
        -H"sender_address: mn45zPRtyy159spQ77gR43NoJmZiw2fN3a" \
        -H"signature: IMiZ0ZJhC5kdORnGnfwBJm7ikyDSrl0Icqepd6XZIJCynYd5GLITTCbk4vCxuvGgnj4Z24ay6niXmqFxkctqu8U" \
        /api/audit/ 
```

>The above command returns JSON structured like this:

```json
{
  "data_hash": "3a6eb0790f39ac87c94f3856b2dd2c5d110e6811602261a9a923d3bb23adc8b7",
  "challenge_seed": "19b25856e1c150ca834cffc8b59b23adbd0ec0389e58eb22b3b64768098d002b",
  "challenge_response": "a068cf9870a41ecc36e18be9277bc353f88e29ad8a1b2a778581b37453de7692"
}
```


User can upload data via POST to an end node.

### HTTP Request

`POST /api/audit/`

### Query Parameters

Type | Params | Values | Description
--------- | ------- | ----------- | ----------------
POST | data_hash | string | data_hash must be sent with each request. It ensures that the data passed to the endpoint has not been modified in transit. data_hash should be the SHA-256 hash of file_data
POST | challenge_seed | string | A SHA-256 hash of that you would like to add to the file data to generate a challenge response.
HEADER | sender_address | string | The Bitcoin public key of the user that is trying to POST data.
HEADER | signature | string | Produced by signing `data_hash` by the private key belonging to `sender_address`.


# Serve files

User can download encrypted data (for allowed files) via GET from an end node using a decryption key.

Type | Params | Values | Description
--------- | ------- | ----------- | ----------------
HEADER | sender_address | string | The Bitcoin public key of the user that is trying to POST data.
HEADER | signature | string | Produced by signing `data_hash` by the private key belonging to `sender_address`.

>To download data, use this code:

```shell
curl
    -X GET -H "Content-type: application/json" \
    -H "Accept: application/json" \
    -H"sender_address: mn45zPRtyy159spQ77gR43NoJmZiw2fN3a" \
    -H"signature: IMiZ0ZJhC5kdORnGnfwBJm7ikyDSrl0Icqepd6XZIJCynYd5GLITTCbk4vCxuvGgnj4Z24ay6niXmqFxkctqu8U" \
    /api/files/3a6eb0790f39ac87c94f3856b2dd2c5d110e6811602261a9a923d3bb23adc8b7?decryption_key=%A3%B4e%EA%82%00%22%3A%C3%86%C0hn1%B3%F7%F7%F8%8EL7S%F3D%28%7C%85%95%CE%9D%D5B&file_alias=data.txt
```

> The above command returns binary file data as `file_name`.

### HTTP Request

`GET /api/files/<data_hash>?decryption_key=<decryption_key>&file_alias=<file_alias>`


