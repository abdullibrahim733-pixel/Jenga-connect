from django.shortcuts import get_object_or_404
from django.db import connection
from django.core.cache import cache
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    AllowAny,
)
from core.models import (
    Profile,
    HardwareStore,
    Product,
    Order,
    Notification,
)
from .serializers import (
    ProfileSerializer,
    HardwareStoreSerializer,
    ProductSerializer,
    OrderSerializer,
    NotificationSerializer,
    PlaceOrderSerializer,
)
import math
from core.services import create_order_with_items

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    health = {
        "status": "healthy",
        "database": "unknown",
        "cache": "unknown",
    }

    try:
        connection.ensure_connection()
        health["database"] = "connected"
    except Exception as e:
        health["status"] = "unhealthy"
        health["database"] = f"error: {str(e)}"

    try:
        cache.set("health_check", "ok", 10)
        if cache.get("health_check") == "ok":
            health["cache"] = "connected"
    except Exception as e:
        health["cache"] = f"unavailable: {str(e)}"

    status_code = 200 if health["status"] == "healthy" else 503
    return Response(health, status=status_code)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all().select_related("user")
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return qs.none()
        if profile.role == "admin":
            return qs
        return qs.filter(id=profile.id)


class HardwareStoreViewSet(viewsets.ModelViewSet):
    queryset = HardwareStore.objects.filter(active=True).select_related("owner")
    serializer_class = HardwareStoreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        radius = float(request.query_params.get("radius", 10))

        if not lat or not lng:
            return Response(
                {"detail": "lat and lng are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return Response(
                {"detail": "lat and lng must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stores = HardwareStore.objects.filter(
            active=True, latitude__isnull=False, longitude__isnull=False
        )
        nearby_stores = []
        for store in stores:
            distance = haversine_distance(lat, lng, store.latitude, store.longitude)
            if distance <= radius:
                store_data = HardwareStoreSerializer(store).data
                store_data["distance_km"] = round(distance, 2)
                nearby_stores.append(store_data)

        nearby_stores.sort(key=lambda x: x["distance_km"])
        return Response(nearby_stores)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(active=True).select_related("store")
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        category = self.request.query_params.get("category")
        qs = super().get_queryset()
        if category:
            qs = qs.filter(category=category)
        return qs

    def perform_create(self, serializer):
        profile = self.request.user.profile
        if profile.role == "hardware":
            store = HardwareStore.objects.filter(owner=profile).first()
            if store:
                serializer.save(store=store)
            else:
                serializer.save()
        else:
            serializer.save()

    def perform_destroy(self, instance):
        profile = self.request.user.profile
        if profile.role == "hardware" and instance.store.owner != profile:
            return
        instance.delete()


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related("fundi", "store").prefetch_related(
        "items__product"
    )
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        profile = self.request.user.profile
        if profile.role == "admin":
            return qs
        if profile.role == "hardware":
            return qs.filter(store__owner=profile)
        return qs.filter(fundi=profile)

    @action(detail=False, methods=["post"])
    def place_order(self, request):
        """
        Expected payload:
        {
            "fundi_id": "uuid",
            "delivery_area": "Arusha CBD",
            "delivery_address_note": "Near the clock tower",
            "items": [
                {"product_id": "uuid", "quantity": 10}
            ]
        }
        """
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        fundi = get_object_or_404(Profile, id=data["fundi_id"], role="fundi")
        if request.user.profile.role != "admin" and fundi.id != request.user.profile.id:
            return Response(
                {"detail": "You can only place orders for your own account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        items_payload = data["items"]
        product_ids = [item["product_id"] for item in items_payload]
        products = {
            product.id: product
            for product in Product.objects.filter(id__in=product_ids, active=True)
        }

        items = []
        for item in items_payload:
            product = products.get(item["product_id"])
            if not product:
                return Response(
                    {"detail": f"Product {item['product_id']} not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            items.append({"product": product, "quantity": item["quantity"]})

        try:
            order = create_order_with_items(
                fundi=fundi,
                delivery_area=data["delivery_area"].strip(),
                delivery_address_note=(data.get("delivery_address_note") or "").strip(),
                items=items,
            )
        except ValueError as exc:
            logger.warning("Order placement failed: %s", exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().select_related("user", "order")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user.profile)

    @action(detail=False, methods=["post"])
    def mark_read(self, request):
        notification_ids = request.data.get("notification_ids", [])
        Notification.objects.filter(
            id__in=notification_ids, user=request.user.profile
        ).update(is_read=True)
        return Response({"status": "marked as read"})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(
            user=request.user.profile, is_read=False
        ).count()
        return Response({"unread_count": count})
