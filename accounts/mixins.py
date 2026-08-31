class OrganisationScopedMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request.user, "organisation", None)
        if org is None:
            return qs.none()
        return qs.filter(organisation=org)

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation)
