from django.shortcuts import render,get_object_or_404, redirect
from .models import Product, Order, OrderItem, ProductReview
from django.db.models import Q
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
# Create your views here.
    
def home(request):
    sort_by = request.GET.get('sort', '')
    query = request.GET.get('q', '')
    selected_category = request.GET.get('category', '')

    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
        )

    
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-id')
    else:
        products = products.order_by('id')


    categories = (
        Product.objects
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    cart_count = sum(request.session.get('cart', {}).values())

    context = {
    'products': page_obj,
    'page_obj': page_obj,
    'query': query,
    'categories': categories,
    'selected_category': selected_category,
    'sort_by': sort_by,
    'cart_count': cart_count,
    }

    return render(request, 'products/home.html', context)



def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = ProductReview.objects.filter(
        product=product
    ).select_related('user')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in to submit a review.')
            return redirect('login')

        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not rating.isdigit() or not 1 <= int(rating) <= 5:
            messages.error(request, 'Please select a rating from 1 to 5.')
        elif not comment:
            messages.error(request, 'Please write a review.')
        elif ProductReview.objects.filter(
            product=product, user=request.user
        ).exists():
            messages.error(request, 'You have already reviewed this product.')
        else:
            ProductReview.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                comment=comment,
            )
            messages.success(request, 'Your review has been submitted!')
            return redirect('product_detail', product_id=product.id)

    return render(
        request,
        'products/product_detail.html',
        {'product': product, 'reviews': reviews}
    )


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart = request.session.get('cart', {})

    product_id = str(product.id)
    cart[product_id] = cart.get(product_id, 0) + 1

    request.session['cart'] = cart

    return redirect('cart')


def cart(request):
    cart_items = request.session.get('cart', {})
    products = Product.objects.filter(id__in=cart_items.keys())

    items = []
    total = 0

    for product in products:
        quantity = cart_items[str(product.id)]
        subtotal = product.price * quantity
        total += subtotal

        items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    return render(request, 'products/cart.html', {
        'items': items,
        'total': total,
    })

def remove_from_cart(request, product_id):
    cart_items = request.session.get('cart', {})

    product_id = str(product_id)

    if product_id in cart_items:
        del cart_items[product_id]

    request.session['cart'] = cart_items

    return redirect('cart')


def update_cart(request, product_id):
    if request.method == 'POST':
        cart_items = request.session.get('cart', {})
        product_id = str(product_id)

        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        if quantity <= 0:
            cart_items.pop(product_id, None)
        else:
            if product_id in cart_items:
                cart_items[product_id] = quantity

        request.session['cart'] = cart_items

    return redirect('cart')



def checkout(request):
    
    cart_items = request.session.get('cart', {})
    products = Product.objects.filter(id__in=cart_items.keys())

    items = []
    total = 0
    stock_error = ''

    for product in products:
        quantity = cart_items[str(product.id)]
        subtotal = product.price * quantity
        total += subtotal

        items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()


        stock_error = ''

        for item in items:
            if item['quantity'] > item['product'].stock:
                stock_error = (
                    f"Sorry, only {item['product'].stock} units of "
                    f"{item['product'].name} are available."
                )
                break


        
        if (full_name and email and address and phone.isdigit() and len(phone) == 10 and items and not stock_error):
            
            with transaction.atomic():
            # Recheck stock immediately before saving the order.
                for item in items:
                    product = Product.objects.select_for_update().get(id=item['product'].id)
                if item['quantity'] > product.stock:
                    message = (f"Sorry, only {product.stock} units of " f"{product.name} are available.")
                    return render(request, 'products/checkout.html', {'items': items, 'total': total, 'message': message},)

             # Reduce stock for each ordered product.
                for item in items:
                    product = Product.objects.select_for_update().get(id=item['product'].id)
                    product.stock -= item['quantity']
                    product.save(update_fields=['stock'])

            order = Order.objects.create(user=request.user if request.user.is_authenticated else None, full_name=full_name, email=email, phone=phone, address=address, total_amount=total,)
            
            for item in items:
                OrderItem.objects.create(order=order, product=item['product'], product_name=item['product'].name, price=item['product'].price, quantity=item['quantity'],)


            request.session['cart'] = {}
            return redirect('order_confirmation', order_id=order.id)


    
        else:
            if stock_error:
                message = stock_error
            else:
                message = 'Please enter valid details and ensure your cart is not empty.'

            return render(request, 'products/checkout.html',{ 'items': items, 'total': total, 'message': message,})
        
    return render(request, 'products/checkout.html', {'items': items,'total': total,})



@login_required(login_url='login')
def order_confirmation(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
    )

    return render(
        request,
        'products/order_confirmation.html',
        {'order': order},
    )




def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(
        request,
        'registration/register.html',
        {'form': form},
    )


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'products/my_orders.html',
        {'orders': orders},
    )


@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
    )

    return render(
        request,
        'products/order_detail.html',
        {'order': order},
    )



@login_required(login_url='login')
def cancel_order(request, order_id):
    if request.method != 'POST':
        return redirect('order_detail', order_id=order_id)

    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(),
            id=order_id,
            user=request.user,
        )

        if order.status not in ['pending', 'processing']:
            return redirect('order_detail', order_id=order.id)

        order_items = list(
            order.items.select_related('product').all()
        )

        for item in order_items:
            product = Product.objects.select_for_update().get(
                id=item.product_id
            )
            product.stock += item.quantity
            product.save(update_fields=['stock'])

        order.status = 'cancelled'
        order.save(update_fields=['status'])

    return redirect('order_detail', order_id=order.id)



