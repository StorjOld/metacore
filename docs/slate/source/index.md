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
        -F"file_role=3" -F"file_data=@file_name" \
        /api/files/ 
```

>The above command returns JSON structured like this:

```json
{
  "data_hash": "3b438fd7b1f223890f18f8ffc50c19c00b08340fc4fc76a94ba3a1c160b332a0",
  "file_role": 0
}
```


User can upload data via POST to an end node.

### HTTP Request

`POST /api/files`

### Query Parameters

Type | Params | Values | Description
--------- | ------- | ----------- | ----------------
POST | data_hash | string | data_hash must be sent with each request. It ensures that the data passed to the endpoint has not been modified in transit. data_hash should be the SHA-256 hash of file_data
POST | file_role | integer | The uploading party needs to be able to set file roles. For example, if anyone can retrieve this file or only specified addresses. file_role have not been defined yet, so we just store whatever is passed and move on.
POST | file_data | binary file | Encrypted shard of the data. To ensure properly handling under the current specifications file_data should not be larger than 128 MB


# File Download

User can download data via GET from an end node.

>To download data, use this code:

```shell
curl
    -X GET -H "Content-type: application/json" \
    -H "Accept: application/json" \
    /api/files/3b438fd7b1f223890f18f8ffc50c19c00b08340fc4fc76a94ba3a1c160b332a0
```

> The above command returns JSON structured like this:
```binary data
....binary data goes here...
```

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
