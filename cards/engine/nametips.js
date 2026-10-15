// Name tips: a short footer on a card back saying what a hard place name means.
// They are NOT from the sheet, so they never appear on a card front, never become an answer and are never tested.
// Only exact names listed here get a tip. No rules like "every -ham means home": Durham and Oldham would be wrong.
// Leave out any name whose origin is uncertain or disputed (e.g. London, Lagan).
// Entries were drafted from standard place-name explanations and should be confirmed by a person before wide use.

export const NAME_TIPS = {
  belfast: 'From the Irish Béal Feirste: “mouth of the sandbank ford”, a river crossing.',
  birmingham: '“-ham” is an old English word for home.',
  cardiff: 'Its Welsh name is Caerdydd. “Caer” means fort.',
  edinburgh: '“-burgh” means a fort or walled town.',
};

export function nameTip(name) {
  return NAME_TIPS[String(name).trim().toLowerCase()] || null;
}
