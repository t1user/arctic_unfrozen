# Python 3 Compatibility Notes

This document records compatibility issues that may affect Arctic on supported
Python 3 versions.

## Trying to store numpy types with bson

Currently if you try and store (say) a numpy integer in BSONStore you will get an encoding failure:  
`In [14]:  lib.insert_one({'a': np.int64(1)})`

```python
    101     request_id, msg, size = message.query(flags, ns, 0, -1, spec,
--> 102                                           None, codec_options, check_keys)
    103 
    104     if (max_bson_size is not None

InvalidDocument: Cannot encode object: 1
```
This is because numpy scalar types are not JSON/BSON serializable and can produce
confusing errors in older PyMongo versions: https://jira.mongodb.org/browse/PYTHON-1664

Arctic does not do the conversion to int from numpy.int types and you should ensure you convert it before passing
the parameters to insert / update functions in BSONStore or wherever there is a bson.encode involved

## Python 2 compatibility

Python 2 compatibility is no longer a target for this revived package. Do not
expect data written by current Python 3 versions to be readable from Python 2.

## Byte strings in column or index names

Byte-string data or labels can break workflows that expect text strings.

If you hit this issue, a workaround is to set: [FORCE_BYTES_TO_UNICODE](https://github.com/manahl/arctic/blob/master/arctic/_config.py#L92)
which will explicitly convert byte values and labels to text. This conversion is
linear and should not be used for normal write/read flows.
