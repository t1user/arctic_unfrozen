from mock import patch

from arctic import auth


def test_create_client_without_credentials():
    with patch("arctic.auth.MongoClient", autospec=True) as mongo_client, \
         patch("arctic.hooks.get_mongodb_uri", return_value="mongodb://host") as get_mongodb_uri:
        assert auth.create_client("host") is mongo_client.return_value

    get_mongodb_uri.assert_called_once_with("host")
    mongo_client.assert_called_once_with("mongodb://host")


def test_create_client_with_credentials():
    credentials = auth.MongoCredentials(database="admin", user="user", password="password")
    with patch("arctic.auth.MongoClient", autospec=True) as mongo_client, \
         patch("arctic.hooks.get_mongodb_uri", return_value="mongodb://host"):
        assert auth.create_client("host", credentials, appname="arctic") is mongo_client.return_value

    mongo_client.assert_called_once_with(
        "mongodb://host",
        username="user",
        password="password",
        authSource="admin",
        appname="arctic",
    )
