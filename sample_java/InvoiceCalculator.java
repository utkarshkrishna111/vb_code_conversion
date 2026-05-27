package com.example.billing;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/**
 * Calculates invoice totals, applies discounts, and computes VAT
 * for a retail billing system.
 */
public class InvoiceCalculator {

    public static final BigDecimal MAX_DISCOUNT = new BigDecimal("0.30");
    public static final BigDecimal DEFAULT_VAT  = new BigDecimal("0.20");

    // ── Data classes ──────────────────────────────────────────────────────

    public static class LineItem {
        private final String     productCode;
        private final String     description;
        private final int        quantity;
        private final BigDecimal unitPrice;

        public LineItem(String productCode, String description,
                        int quantity, BigDecimal unitPrice) {
            this.productCode = productCode;
            this.description = description;
            this.quantity    = quantity;
            this.unitPrice   = unitPrice;
        }

        public String     getProductCode() { return productCode; }
        public String     getDescription() { return description; }
        public int        getQuantity()    { return quantity; }
        public BigDecimal getUnitPrice()   { return unitPrice; }
    }

    public static class Invoice {
        private final String         invoiceNumber;
        private final String         customerId;
        private final List<LineItem> items;
        private final BigDecimal     discountPct;
        private final BigDecimal     vatRate;

        public Invoice(String invoiceNumber, String customerId,
                       List<LineItem> items,
                       BigDecimal discountPct, BigDecimal vatRate) {
            this.invoiceNumber = invoiceNumber;
            this.customerId    = customerId;
            this.items         = items;
            this.discountPct   = discountPct;
            this.vatRate       = vatRate;
        }

        public String         getInvoiceNumber() { return invoiceNumber; }
        public String         getCustomerId()    { return customerId; }
        public List<LineItem> getItems()         { return items; }
        public BigDecimal     getDiscountPct()   { return discountPct; }
        public BigDecimal     getVatRate()       { return vatRate; }
    }

    // ── Business logic ────────────────────────────────────────────────────

    /**
     * Calculates the subtotal as the sum of (quantity × unitPrice) for all line items.
     */
    public BigDecimal calcSubtotal(Invoice invoice) {
        BigDecimal total = BigDecimal.ZERO;
        for (LineItem item : invoice.getItems()) {
            BigDecimal lineTotal = item.getUnitPrice()
                    .multiply(new BigDecimal(item.getQuantity()));
            total = total.add(lineTotal);
        }
        return total.setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Applies a percentage discount to the subtotal.
     *
     * @throws IllegalArgumentException if discountPct is negative or exceeds MAX_DISCOUNT (0.30)
     */
    public BigDecimal applyDiscount(BigDecimal subtotal, BigDecimal discountPct) {
        if (discountPct.compareTo(BigDecimal.ZERO) < 0
                || discountPct.compareTo(MAX_DISCOUNT) > 0) {
            throw new IllegalArgumentException(
                    "Discount out of range: " + discountPct
                    + " (must be 0.00–" + MAX_DISCOUNT + ")");
        }
        BigDecimal multiplier = BigDecimal.ONE.subtract(discountPct);
        return subtotal.multiply(multiplier).setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Calculates the VAT amount for a given base amount and VAT rate.
     */
    public BigDecimal calcVAT(BigDecimal amount, BigDecimal vatRate) {
        return amount.multiply(vatRate).setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Calculates the invoice grand total: (subtotal − discount) + VAT.
     *
     * @throws IllegalArgumentException if the invoice's discountPct is out of range
     */
    public BigDecimal calcTotal(Invoice invoice) {
        BigDecimal subtotal    = calcSubtotal(invoice);
        BigDecimal discounted  = applyDiscount(subtotal, invoice.getDiscountPct());
        BigDecimal vat         = calcVAT(discounted, invoice.getVatRate());
        return discounted.add(vat).setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Prints a formatted invoice summary to standard output.
     */
    public void printInvoiceSummary(Invoice invoice) {
        BigDecimal total = calcTotal(invoice);
        System.out.println("Invoice:          " + invoice.getInvoiceNumber());
        System.out.println("Customer:         " + invoice.getCustomerId());
        System.out.printf ("Total (inc VAT):  %.2f%n", total);
    }
}
