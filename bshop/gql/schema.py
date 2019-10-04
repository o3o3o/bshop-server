import graphene
from graphene_django.debug import DjangoDebug

from user_center.schema import Query as UserQuery, Mutation as UserMutation

from wallet.schema import Query as WalletQuery, Mutation as WalletMutation


class Query(UserQuery, WalletQuery, graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name="_debug")


class Mutation(UserMutation, WalletMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=True)
