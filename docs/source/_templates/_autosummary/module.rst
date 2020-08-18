{{ fullname | escape | underline}}


.. automodule:: {{ fullname }}
   :members:
   :undoc-members:
   :private-members:
   :show-inheritance:
   :ignore-module-all:
   :exclude-members: '__init__'

   {% if classes %}
   .. only:: not rinoh

       Inheritance diagrams
       ^^^^^^^^^^^^^^^^^^^^

       .. inheritance-diagram:: {{ fullname }}

   {% endif %}


   {% block modules %}
   {% if modules %}
   .. rubric:: Modules

   .. autosummary::
      :toctree:
      :recursive:
      :template: _autosummary/module.rst
   {% for item in modules %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   .. ifconfig:: "{{fullname | escape }}" == "{{module | escape}}"

      Package Contents
      ^^^^^^^^^^^^^^^^

   .. ifconfig:: "{{fullname | escape }}" != "{{module | escape}}"

      Module Contents
      ^^^^^^^^^^^^^^^

   {% block attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Module Attributes') }}

   .. autosummary::
   {% for item in attributes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if functions %}
   .. rubric:: {{ _('Functions') }}

   .. autosummary::
   {% for item in functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if classes %}
   .. rubric:: {{ _('Classes') }}

   .. autosummary::
      :template: _autosummary/class.rst
   {% for item in classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: {{ _('Exceptions') }}

   .. autosummary::
   {% for item in exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}
