# Errors

<aside class="notice">The MetaDisk API uses the following error codes:</aside>



Error Code | Meaning
---------- | -------
Transfer errors |
101 | Invalid SHA-256 hash
102 | Data hash doesn't match file data
103 | File data is larger than 128MB
201 | Node has a full disk
202 | Node has reached bandwidth limit
301 | Particular hash not found
401 | Invalid signature
Audit errors |
101 | Invalid SHA-256 hash
102 | Invalid seed
103 | File data is larger than 128MB
301 | Particular hash not found
401 | Invalid signature
