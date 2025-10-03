from rest_framework import serializers
from .models import Link, Node, NodeHealth, NodeConnection


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = '__all__'
        read_only_fields = ('uuid', 'create_time', 'update_time')


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = '__all__'
        read_only_fields = ('uuid', 'create_time', 'update_time', 'is_healthy', 'last_check_time')


class NodeConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeConnection
        fields = '__all__'
        read_only_fields = ('uuid', 'create_time', 'update_time')


class NodeHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeHealth
        fields = '__all__'
        read_only_fields = ('uuid', 'create_time', 'update_time')